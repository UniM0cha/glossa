#include "interpreter-dock.hpp"
#include "interpreter-control.hpp"

#include <QLabel>
#include <QPushButton>
#include <QTimer>
#include <QVBoxLayout>

InterpreterDock::InterpreterDock(QWidget *parent) : QWidget(parent)
{
	auto *layout = new QVBoxLayout(this);
	layout->setContentsMargins(12, 12, 12, 12);
	layout->setSpacing(10);

	status = new QLabel(this);
	status->setAlignment(Qt::AlignCenter);
	status->setWordWrap(true);

	button = new QPushButton(this);
	button->setMinimumHeight(56);

	layout->addWidget(status);
	layout->addWidget(button);
	layout->addStretch();

	connect(button, &QPushButton::clicked, this, &InterpreterDock::onToggle);

	auto *timer = new QTimer(this);
	connect(timer, &QTimer::timeout, this, &InterpreterDock::refresh);
	timer->start(500);

	refresh();
}

void InterpreterDock::onToggle()
{
	interpreter_toggle_all();
	refresh();
}

void InterpreterDock::refresh()
{
	switch (interpreter_state()) {
	case INTERP_NONE:
		status->setText("필터 없음 — 오디오 소스에\n'Live Interpreter' 필터를 추가하세요");
		button->setText("통역 시작");
		button->setEnabled(false);
		button->setStyleSheet("");
		break;
	case INTERP_OFF:
		status->setText("⏸  대기 중 (OFF)");
		button->setText("설교 통역 시작");
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
}
