#pragma once
#include <QWidget>

class QPushButton;
class QLabel;

/* OBS 메인 창에 붙는 통역 ON/OFF 도크 — 버튼 + 상태표시등(LIVE/연결중/OFF). */
class InterpreterDock : public QWidget {
	Q_OBJECT
public:
	explicit InterpreterDock(QWidget *parent = nullptr);

private slots:
	void onToggle();
	void refresh(); /* 500ms 폴링으로 상태 갱신(핫키/체크박스 변경도 반영) */

private:
	QPushButton *button = nullptr;
	QLabel *status = nullptr;
};
