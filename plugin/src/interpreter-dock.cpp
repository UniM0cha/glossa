#include "interpreter-dock.hpp"
#include "interpreter-control.hpp"
#include "interpreter-engine.hpp"

#include <obs.h>

#include <QComboBox>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QListWidgetItem>
#include <QPushButton>
#include <QTimer>
#include <QVBoxLayout>

#include <algorithm>
#include <vector>

/* obs_enum_sources 콜백 — 오디오 출력 플래그가 있는 소스 이름만 수집 */
static bool enum_audio_sources(void *p, obs_source_t *s)
{
	auto *names = static_cast<std::vector<QString> *>(p);
	if (obs_source_get_output_flags(s) & OBS_SOURCE_AUDIO) {
		const char *n = obs_source_get_name(s);
		if (n && *n)
			names->push_back(QString::fromUtf8(n));
	}
	return true;
}

InterpreterDock::InterpreterDock(QWidget *parent) : QWidget(parent)
{
	auto *layout = new QVBoxLayout(this);
	layout->setContentsMargins(12, 12, 12, 12);
	layout->setSpacing(8);

	auto *lblServer = new QLabel("서버 주소 (Server URL)", this);
	serverEdit = new QLineEdit(this);
	auto *lblKey = new QLabel("서비스 키 (Service Key)", this);
	keyEdit = new QLineEdit(this);
	keyEdit->setEchoMode(QLineEdit::Password);
	auto *lblEngine = new QLabel("번역 엔진 (Engine)", this);
	engineBox = new QComboBox(this);
	engineBox->addItem("Gemini (16kHz)", "gemini");
	engineBox->addItem("OpenAI (24kHz)", "openai");

	auto *lblSrc = new QLabel("통역할 오디오 — 체크하면 합성되어 번역됩니다", this);
	lblSrc->setWordWrap(true);
	sourceList = new QListWidget(this);
	sourceList->setMaximumHeight(150);

	status = new QLabel(this);
	status->setAlignment(Qt::AlignCenter);
	status->setWordWrap(true);
	monitor = new QLabel(this);
	monitor->setAlignment(Qt::AlignCenter);
	monitor->setWordWrap(true);
	monitor->setStyleSheet("color:#9aa0a6; font-size:12px;");

	button = new QPushButton(this);
	button->setMinimumHeight(48);

	layout->addWidget(lblServer);
	layout->addWidget(serverEdit);
	layout->addWidget(lblKey);
	layout->addWidget(keyEdit);
	layout->addWidget(lblEngine);
	layout->addWidget(engineBox);
	layout->addWidget(lblSrc);
	layout->addWidget(sourceList);
	layout->addWidget(status);
	layout->addWidget(monitor);
	layout->addWidget(button);
	layout->addStretch();

	connect(button, &QPushButton::clicked, this, &InterpreterDock::onToggle);
	connect(sourceList, &QListWidget::itemChanged, this, &InterpreterDock::onSourceItemChanged);
	connect(serverEdit, &QLineEdit::editingFinished, this, &InterpreterDock::onSettingsChanged);
	connect(keyEdit, &QLineEdit::editingFinished, this, &InterpreterDock::onSettingsChanged);
	connect(engineBox, &QComboBox::currentIndexChanged, this, &InterpreterDock::onSettingsChanged);

	auto *timer = new QTimer(this);
	connect(timer, &QTimer::timeout, this, &InterpreterDock::refresh);
	timer->start(500);

	reloadSettings();
	rebuildSourceList();
	refresh();
}

void InterpreterDock::reloadSettings()
{
	/* 프로그램적으로 채울 때 onSettingsChanged 가 안 튀게 신호 차단 */
	auto &e = InterpreterEngine::instance();
	serverEdit->blockSignals(true);
	serverEdit->setText(QString::fromStdString(e.server_url()));
	serverEdit->blockSignals(false);
	keyEdit->blockSignals(true);
	keyEdit->setText(QString::fromStdString(e.service_key()));
	keyEdit->blockSignals(false);
	engineBox->blockSignals(true);
	int idx = engineBox->findData(QString::fromStdString(e.engine()));
	if (idx >= 0)
		engineBox->setCurrentIndex(idx);
	engineBox->blockSignals(false);
}

void InterpreterDock::rebuildSourceList()
{
	buildingList = true;
	auto selected = InterpreterEngine::instance().selected_sources();
	sourceList->clear();
	std::vector<QString> names;
	obs_enum_sources(enum_audio_sources, &names);
	for (const auto &name : names) {
		auto *item = new QListWidgetItem(name, sourceList);
		item->setFlags(item->flags() | Qt::ItemIsUserCheckable);
		bool on = std::find(selected.begin(), selected.end(), name.toStdString()) != selected.end();
		item->setCheckState(on ? Qt::Checked : Qt::Unchecked);
	}
	buildingList = false;
}

void InterpreterDock::onSourceItemChanged(QListWidgetItem *)
{
	if (buildingList)
		return;
	std::vector<std::string> names;
	for (int i = 0; i < sourceList->count(); i++) {
		auto *it = sourceList->item(i);
		if (it->checkState() == Qt::Checked)
			names.push_back(it->text().toStdString());
	}
	InterpreterEngine::instance().set_selected_sources(names);
}

void InterpreterDock::onSettingsChanged()
{
	InterpreterEngine::instance().configure(serverEdit->text().toStdString(), keyEdit->text().toStdString(),
						engineBox->currentData().toString().toStdString());
}

void InterpreterDock::onToggle()
{
	InterpreterEngine::instance().toggle();
	refresh();
}

void InterpreterDock::refresh()
{
	switch (InterpreterEngine::instance().state()) {
	case INTERP_NONE:
		status->setText("통역할 오디오 소스를\n위에서 체크하세요");
		button->setText("통역 시작");
		button->setEnabled(false);
		button->setStyleSheet("");
		break;
	case INTERP_OFF:
		status->setText("⏸  대기 중 (OFF)");
		button->setText("통역 시작");
		button->setEnabled(true);
		button->setStyleSheet("background:#2563eb; color:white; font-weight:bold; font-size:15px;");
		break;
	case INTERP_CONNECTING:
		status->setText("●  서버 연결 중…");
		button->setText("통역 중지");
		button->setEnabled(true);
		button->setStyleSheet("background:#d97706; color:white; font-weight:bold; font-size:15px;");
		break;
	case INTERP_LIVE:
		status->setText("🔴  통역 중 (LIVE)");
		button->setText("통역 중지");
		button->setEnabled(true);
		button->setStyleSheet("background:#dc2626; color:white; font-weight:bold; font-size:15px;");
		break;
	}

	/* 모니터링 패널 */
	ServerStatus st = InterpreterEngine::instance().status();
	if (st.live) {
		int s = st.durationSec;
		QString dur = QString::asprintf("%d:%02d:%02d", s / 3600, (s % 3600) / 60, s % 60);
		QStringList parts;
		for (const auto &kv : st.listeners)
			parts << QString("%1 %2").arg(QString::fromStdString(kv.first)).arg(kv.second);
		QString br = parts.isEmpty() ? QString("청취자 없음") : ("청취자 " + QString::number(st.total) +
									 "명 (" + parts.join(" · ") + ")");
		monitor->setText(QString("⏱ %1   |   %2   |   엔진: %3")
					 .arg(dur, br, QString::fromStdString(st.engine)));
	} else {
		monitor->setText("— 서버 대기 중 —");
	}
}
