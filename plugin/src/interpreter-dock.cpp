#include "interpreter-dock.hpp"
#include "interpreter-control.hpp"
#include "interpreter-engine.hpp"

#include <obs.h>

#include <QCheckBox>
#include <QComboBox>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QListWidgetItem>
#include <QPushButton>
#include <QTimer>
#include <QVBoxLayout>

#include <algorithm>
#include <thread>
#include <vector>

#include <QMetaObject>

#include <ixwebsocket/IXHttpClient.h>
#include <nlohmann/json.hpp>

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

	auto *lblServer = new QLabel("서버 주소 (청취 페이지 URL)", this);
	serverEdit = new QLineEdit(this);
	serverEdit->setPlaceholderText("https://your-host.example.com");
	auto *lblKey = new QLabel("서비스 키 (Service Key)", this);
	keyEdit = new QLineEdit(this);
	keyEdit->setEchoMode(QLineEdit::Password);
	auto *lblEngine = new QLabel("번역 엔진 (Engine)", this);
	engineBox = new QComboBox(this);
	engineBox->addItem("Gemini (16kHz)", "gemini");
	engineBox->addItem("OpenAI (24kHz)", "openai");

	auto *lblVoice = new QLabel("설교자 음색 (Voice)", this);
	voiceBox = new QCheckBox("설교자 본인 목소리로 변환", this);
	speakerBox = new QComboBox(this);
	speakerBox->setEnabled(false); /* 서버에서 목록 받기 전엔 비활성 — fetchSpeakers 가 채운다 */

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
	layout->addWidget(lblVoice);
	layout->addWidget(voiceBox);
	layout->addWidget(speakerBox);
	layout->addWidget(lblSrc);
	layout->addWidget(sourceList);
	layout->addWidget(status);
	layout->addWidget(monitor);
	layout->addWidget(button);
	layout->addStretch();

	connect(button, &QPushButton::clicked, this, &InterpreterDock::onToggle);
	connect(sourceList, &QListWidget::itemChanged, this, &InterpreterDock::onSourceItemChanged);
	/* 주소/키 확정 시 먼저 엔진에 저장(onSettingsChanged) → 그 값으로 설교자 목록 재조회(fetchSpeakers) */
	connect(serverEdit, &QLineEdit::editingFinished, this, &InterpreterDock::onSettingsChanged);
	connect(serverEdit, &QLineEdit::editingFinished, this, &InterpreterDock::fetchSpeakers);
	connect(keyEdit, &QLineEdit::editingFinished, this, &InterpreterDock::onSettingsChanged);
	connect(keyEdit, &QLineEdit::editingFinished, this, &InterpreterDock::fetchSpeakers);
	connect(engineBox, &QComboBox::currentIndexChanged, this, &InterpreterDock::onSettingsChanged);
	connect(speakerBox, &QComboBox::currentIndexChanged, this, &InterpreterDock::onSettingsChanged);
	connect(voiceBox, &QCheckBox::toggled, this, &InterpreterDock::onSettingsChanged);

	auto *timer = new QTimer(this);
	connect(timer, &QTimer::timeout, this, &InterpreterDock::refresh);
	timer->start(500);

	reloadSettings();
	rebuildSourceList();
	refresh();
	fetchSpeakers(); /* 저장된 서버 주소로 설교자 목록 초기 로드 */
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
	speakerBox->blockSignals(true);
	int sidx = speakerBox->findData(QString::fromStdString(e.speaker()));
	if (sidx >= 0)
		speakerBox->setCurrentIndex(sidx);
	speakerBox->blockSignals(false);
	voiceBox->blockSignals(true);
	voiceBox->setChecked(e.voice_conversion());
	voiceBox->blockSignals(false);
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
						engineBox->currentData().toString().toStdString(),
						speakerBox->currentData().toString().toStdString(),
						voiceBox->isChecked());
}

void InterpreterDock::onToggle()
{
	InterpreterEngine::instance().toggle();
	refresh();
}

void InterpreterDock::refresh()
{
	auto &eng = InterpreterEngine::instance();
	status->setStyleSheet(""); /* 매 갱신마다 리셋 — ERROR 빨강이 다른 상태로 남지 않게 */
	switch (eng.state()) {
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
	case INTERP_ERROR:
		status->setStyleSheet("color:#dc2626; font-weight:bold;");
		status->setText("⚠  연결 실패\n" + QString::fromStdString(eng.connection_error()));
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

/* ───────────────── 설교자 목록 (서버 /speakers 동적 조회) ───────────────── */
void InterpreterDock::fetchSpeakers()
{
	auto &eng = InterpreterEngine::instance();
	std::string server = eng.server_url();
	std::string url = eng.http_base() + "/speakers?key=" + eng.service_key();
	int gen = ++fetchGen_;

	if (server.empty()) { /* 주소 미입력 — 네트워크 시도 없이 안내만 */
		populateSpeakers({}, false, gen);
		return;
	}

	/* HTTP GET 은 워커 스레드에서(아키텍처 규칙: GUI/콜백 비블로킹). 결과는 GUI 스레드로 큐잉. */
	std::thread([this, url, gen]() {
		std::vector<std::pair<std::string, std::string>> list;
		bool ok = false;
		ix::HttpClient client(false);
		auto args = client.createRequest();
		args->connectTimeout = 5;
		args->transferTimeout = 5;
		auto resp = client.get(url, args);
		if (resp && resp->statusCode == 200) {
			auto j = nlohmann::json::parse(resp->body, nullptr, false);
			if (j.is_array()) {
				ok = true;
				for (const auto &e : j) {
					std::string k = e.value("key", std::string());
					std::string l = e.value("label", std::string());
					if (!k.empty())
						list.emplace_back(k, l.empty() ? k : l);
				}
			}
		}
		QMetaObject::invokeMethod(
			this, [this, list, ok, gen]() { populateSpeakers(list, ok, gen); }, Qt::QueuedConnection);
	}).detach();
}

void InterpreterDock::populateSpeakers(const std::vector<std::pair<std::string, std::string>> &list, bool ok,
				       int gen)
{
	if (gen != fetchGen_.load())
		return; /* 더 최신 요청이 진행 중 → 이 응답은 버린다 */

	auto &eng = InterpreterEngine::instance();
	std::string prev = eng.speaker(); /* 기존 선택 복원용 */
	bool has = !list.empty();

	speakerBox->blockSignals(true);
	voiceBox->blockSignals(true);
	speakerBox->clear();
	if (has) {
		for (const auto &p : list)
			speakerBox->addItem(QString::fromStdString(p.second), QString::fromStdString(p.first));
		int idx = speakerBox->findData(QString::fromStdString(prev));
		speakerBox->setCurrentIndex(idx >= 0 ? idx : 0);
	} else {
		const char *msg = eng.server_url().empty() ? "서버 주소를 먼저 입력하세요"
				  : ok                       ? "등록된 설교자가 없습니다"
							     : "설교자 목록을 불러오지 못했습니다";
		speakerBox->addItem(msg); /* data 없음 → 선택해도 speaker 미설정 */
		voiceBox->setChecked(false);
	}
	speakerBox->setEnabled(has);
	voiceBox->setEnabled(has);
	speakerBox->blockSignals(false);
	voiceBox->blockSignals(false);

	onSettingsChanged(); /* 현재 speakerBox 선택 + voiceBox 상태를 엔진에 1회 반영 */
}
