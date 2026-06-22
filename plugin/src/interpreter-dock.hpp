#pragma once
#include <QWidget>

class QPushButton;
class QLabel;
class QListWidget;
class QListWidgetItem;
class QLineEdit;
class QComboBox;
class QCheckBox;

/* 통역 도크 — 통역할 오디오 소스 체크 + 서버/엔진 설정 + 시작/중지 + 서버 모니터링. */
class InterpreterDock : public QWidget {
	Q_OBJECT
public:
	explicit InterpreterDock(QWidget *parent = nullptr);

public slots:
	void rebuildSourceList(); /* 오디오 소스 목록 재구성 (GUI 스레드에서 호출) */
	void reloadSettings();    /* 엔진 설정값을 입력 필드에 로드 (config 로드 후) */

private slots:
	void onToggle();
	void onSourceItemChanged(QListWidgetItem *item);
	void onSettingsChanged();
	void refresh(); /* 500ms 폴링: 상태등 + 모니터링 갱신 */

private:
	QLineEdit *serverEdit = nullptr;
	QLineEdit *keyEdit = nullptr;
	QComboBox *engineBox = nullptr;
	QComboBox *speakerBox = nullptr;
	QCheckBox *voiceBox = nullptr;
	QListWidget *sourceList = nullptr;
	QLabel *status = nullptr;
	QLabel *monitor = nullptr;
	QPushButton *button = nullptr;
	bool buildingList = false; /* 재구성 중 itemChanged 무시 */
};
