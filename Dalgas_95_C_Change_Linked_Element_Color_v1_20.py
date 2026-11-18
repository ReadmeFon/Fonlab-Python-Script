#FLM: Cluade: 95_C_Change Linked Element Color
"""
version_1.20
FontLab 8: 선택한 shape와 Element Reference로 연결된 모든 shape의 Fill Color를 변경합니다.
parent=None 독립 창으로 생성 (FontLab 종료 감지는 closeEvent에서 수행)
[웹브라우저 백그라운드 우회 가드(WebBrowser BG Bypass Guard) 적용]


작동 방식:
1. 현재 글리프에서 shape를 선택
2. 스크립트에서 원하는 색상 선택 후 Apply 버튼 클릭
3. 선택한 shape의 shapeData ID를 찾음
4. 폰트 전체에서 동일한 shapeData ID를 가진 모든 shapes를 찾아 색상 변경


v.1.3 : 'Delta Filter가 적용된 Shape 포함' 옵션 추가
   - 기본값은 미체크(제외) 상태이며, 체크 시 Delta Filter가 적용된 Shape의
     색상도 함께 변경하고, Element 패널에 표시되는 원본 Shape
     (shape.includesList[0])의 색상도 함께 변경한다.
v.1.4 : Delta Filter가 적용된 Linked Shape 색상 변경옵션 추가
   - Delta Filter가 적용된 Shape는
     own.shapeData가 None이 아니라, 필터 적용 시점에 FontLab이 그 Shape
     전용으로 새로 발급한 별도의 ID를 갖는다. 즉 단순 Link shape들이 공유하는
     shapeData ID와는 다른 값이므로, own.shapeData로 비교하면 항상 매칭에
     실패한다. 반면 shape.includesList[0].shapeData.id(Element 패널에
     표시되는 원본 Shape의 ID)는 단순 Link shape들과 동일한 값을 갖는다.
   - 해법: _color15_get_shape_data_id()가 Delta Filter shape를 만나면 own.shapeData를
     아예 무시하고, 무조건 shape.includesList[0].shapeData.id를 사용하도록
     적용했다. (폴백이 아니라 우선순위 판별로 변경)
v.1.5 : 메인 윈도우 레이아웃 조정
   - 메인 윈도우 너비를 260px로 고정(setFixedWidth)
   - 컬러 버튼을 한 줄에 3개씩 배치(총 15개 색상 → 5행 x 3열)
   - 컬러 버튼에 SizePolicy.Expanding을 적용하여 창 너비에 비례해 확장되도록 함
   - 컬러 버튼 상하 padding을 10px → 6px로 축소하여 버튼 높이를 기존 대비 약 80% 수준으로 조정
   - 하단 버튼 영역을 Apply 버튼 하나만 남기고 전체 가로 너비를 차지하도록 변경(Close 버튼 제거)
v.1.6 : 컬러 버튼 및 Apply 버튼 세부 스타일 조정
   - 컬러 버튼 내부의 텍스트 라벨(Black, Red 등)을 제거하고 툴팁(마우스 오버)으로 대체
     → 텍스트 길이에 따른 버튼 너비 불균일 문제 해소, 버튼 너비는 SizePolicy.Expanding으로 계속 균등 분할
   - Apply 버튼 높이를 기존 대비 약 50% 수준으로 축소(font-size 18px→14px, padding 15px→5px)
   - 컬러 버튼에 border-radius: 6px 적용하여 모서리를 살짝 둥글게 처리
v.1.7 : 컬러 버튼 배열 순서 변경
   - Red, Pink, Orange / Hanul, Dark Hanul, Black / Blue, Blue2, Dark Blue /
     Green, Dark Green, Violet / Brown, Dark Brown, Dark Violet 순서로 재배치
v.1.8 : 스크립트 실행 시 창 시작 위치 고정
   - self.move(1569, 570) 호출로 QHD 모니터 기준 x=1569, y=570 위치에서
     창이 시작되도록 설정(기존에는 Qt 기본 동작으로 화면 중앙 부근에서 시작)
v.1.9 : 창 시작 위치 재조정
   - x=1569, y=570 위치가 글리프 캔버스 중앙을 가려서, 오른쪽 패널 열
     (View Shape Coordinates, Dalgas Paste 등)과 같은 x축(1980)에 정렬되도록
     x=1980, y=610으로 변경(Dalgas Paste 패널 바로 아래쪽에 이어서 배치)
v.1.10 : 콘솔(Output 패널) 출력 억제
   - 정상 처리 과정(색상 선택, 색상 적용 진행 상황, 처리 완료 요약 등)에서
     출력되던 print()를 모두 제거했다.
   - 에러/예외 상황(글리프·폰트 없음, 알 수 없는 색상, 선택된 shape 없음,
     색상 적용 중 예외 발생, 선택 토글 중 예외 발생)을 알리는 print()만
     남겨 두었다.
v.1.15 : macOS에서 색상 버튼 3등분 정렬 어긋남 / Apply 버튼 하단 여백 없음 수정
   - 원인: main_layout/row_layout의 여백(setContentsMargins)과 간격(setSpacing),
     색상 버튼의 최소폭(setMinimumWidth)·고정 높이(setFixedHeight)를 전부
     지정하지 않고 Qt의 OS별 기본값(QWindowsStyle/QMacStyle)에 맡기고
     있었다. Windows는 기본값이 보기 좋게 나오지만, macOS는 기본
     margin/spacing 값이 다르고, QPushButton에 setStyleSheet()를 적용하는
     순간 네이티브 버튼 여백/헤일로 렌더링이 꺼지기 때문에 색상 버튼의
     3등분 정렬이 어긋나고(행마다 너비가 미묘하게 달라짐) Apply 버튼
     아래 여백이 사라지는 문제가 있었다.
   - main_layout.setContentsMargins(10, 10, 10, 10) / setSpacing(6) 추가.
   - 각 row_layout에 setSpacing(6) 추가(행 간 버튼 간격을 명시적으로 고정).
   - create_color_button()에서 btn.setMinimumWidth(0)을 추가하여 macOS
     네이티브 최소폭 하한선을 제거, Expanding 정책이 3등분을 정확히
     계산하도록 함. btn.setFixedHeight(32)를 추가하여 버튼 높이도 OS
     기본 sizeHint에 좌우되지 않도록 고정.
v.1.16 : 색상 버튼 줄과 Apply 버튼의 너비가 여전히 어긋나던 문제 추가 수정
   - 원인: v1.15에서 row_layout에 setSpacing(6)은 지정했지만
     setContentsMargins는 지정하지 않았다. Qt 문서상 addLayout()으로 추가한
     하위 레이아웃의 기본 여백은 스타일(QStyle)에서 가져오며 OS별로 다를
     수 있다. Apply 버튼은 하위 레이아웃 없이 main_layout에 직접
     addWidget되어 있어 이 영향을 받지 않으므로, macOS에서 row_layout에만
     스타일 기본 여백이 더 붙어 색상 버튼 줄이 Apply 버튼보다 좁아 보이는
     어긋남이 남아 있었다.
   - row_layout.setContentsMargins(0, 0, 0, 0)을 추가하여 스타일 기본값에
     의존하지 않도록 여백을 0으로 명시 고정했다. row_layout과 main_layout이
     항상 같은 좌우 폭을 쓰게 되어 색상 버튼 줄과 Apply 버튼의 너비가
   OS에 관계없이 정확히 일치한다.
v.1.17 : 세 색상 스크립트 동시 실행 격리
   - 웹브라우저 우회 가드는 이 단독 버전의 기존 True 플래그 구현을 그대로
     공통 기준으로 유지했다.
   - 앱 이름·버전·팔레트·진단 스위치·다이얼로그 클래스와 인스턴스 이름을
     C15 전용 이름으로 분리했다.
   - 다이얼로그를 고유 sys 앵커에 보관하여 재실행 시 삭제하거나 새로 만들지
     않고, 숨겨진 기존 창의 타이머와 종료 연결을 복구한 뒤 재사용한다.
   - 종료 감지 타이머에 다이얼로그 부모를 지정했다.
   - 세 색상 기능이 중첩 진입하지 않도록 프로세스 공통 색상 작업 플래그를
     try/finally로 획득·해제한다.



[v1.18] Dalgas 이니셜 전환.
- 앞부분의 기존 수정·개발 이력은 그대로 보존했다.
- 실행 식별자, 객체명, 공유 설정 키의 기존 이니셜을 Dalgas 계열로 맞췄다.

[v1.19] FontLab Light/Dark Mode 자동 배색과 타이틀바 정리.
- QApplication 전역 팔레트의 Window 역할 밝기로 FontLab UI 모드를 실행 시
  한 번 판별하며, 글립 편집공간의 colorWorkspace는 읽지 않는다.
- Light Mode의 기존 체크박스·Apply 버튼·스와치 테두리 배색은 유지한다.
- Dark Mode에서는 체크박스 글자를 밝게 표시하고, Apply 버튼을 어두운
  배경·밝은 글자·Hover·Pressed 상태가 있는 버튼으로 표시한다.
- 15개 색상 스와치의 실제 RGB 값은 바꾸지 않고 외곽선만 밝게 조정한다.
- View Coordinates와 동일한 창 플래그로 최소화·최대화 단추를 숨긴다.
- 다른 스크립트와 동시에 실행해도 테마 전역 이름이 충돌하지 않도록
  기존 C15 전용 체계에 맞춘 _C15_THEME_* / _c15_theme_* 접두사를 사용한다.
- 같은 FontLab 세션에 남아 있는 v1.18 창을 그대로 재사용하지 않도록 C15 전용
  테마 API 표식을 확인하고, 이전 창만 닫은 뒤 v1.19 창을 새로 생성한다.

[v1.20] 문서 앞부분의 수정·개발 이력 버전 표기를 대괄호 형식으로 통일했다.
버전 항목 사이에는 빈 줄 한 줄을 두었으며 실행 코드는 변경하지 않았다.


[Guard] -------------------------------------------------------------------------------
[웹브라우저 백그라운드 우회 가드 적용]
1. 웹브라우저 재진입 대응은 전역 "웹브라우저 백그라운드 우회 가드
     (WebBrowser BG Bypass Guard)"로 처리한다. 
2. 기존에 설치되어 있던 방어코드 3/4는 삭제했다.
    방어코드1(_is_alive)은 웹브라우저 가드와 무관하게 독립적으로 쓰이고 있어 
    그대로 유지했다.
"""

import fontlab as fl6
import FL as legacy
import sys
from typerig.proxy.fl.objects.glyph import pGlyph
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui import QtGui
from PythonQt import QtCore, QtGui as _C15_THEME_QT_GUI


# ── 스크립트 안정성 확보용 위젯 생존 확인 헬퍼 (_is_alive) ───────────────────────
try:
    import sip as _sip
    def _is_alive(widget):
        try:
            return not _sip.isdeleted(widget)
        except Exception:
            return True
except ImportError:
    def _is_alive(widget):
        return True


# ── 웹브라우저 백그라운드 우회 가드 (WebBrowser BG Bypass Guard) ──────────────
# 외부 링크(예: 우클릭 메뉴의 도움말/포럼 링크)를 열 때 webbrowser.open() 호출을
# 가로채, 실제 오픈 동작은 daemon thread에 위임한다. 메인 GUI 스레드의 메시지
# 큐를 ShellExecuteW의 nested 펌프가 돌지 않게 되므로, Qt/PythonQt 재진입
# 크래시를 피하면서도 브라우저는 정상적으로 열 수 있다. 프로세스 전체에서
# 공유되는 idempotent 패치이며, 이 파일 하나만 닫아도 원복되지 않는다(FontLab
# 재시작 시 초기화). 
import threading as _threading
import webbrowser as _webbrowser

_BG_GUARD_ATTR = '_dalgas_webbrowser_bg_guard'

if not getattr(_webbrowser, _BG_GUARD_ATTR, False):
    _original_webbrowser_open = _webbrowser.open

    def _bg_thread_open(url, new=0, autoraise=True):
        _threading.Thread(
            target=_original_webbrowser_open,
            args=(url,),
            kwargs={'new': new, 'autoraise': autoraise},
            daemon=True,
        ).start()
        return True

    _webbrowser.open = _bg_thread_open
    _webbrowser.open_new = lambda url: _bg_thread_open(url, new=1)
    _webbrowser.open_new_tab = lambda url: _bg_thread_open(url, new=2)
    setattr(_webbrowser, _BG_GUARD_ATTR, True)
# ── WebBrowser BG Bypass Guard End ──────────

# ── C15 전용 앱 이름과 버전
_C15_APP_NAME = 'Change El Color'
_C15_APP_VERSION = 'v1.19'

_C15_THEME_LIGHT = 'light'
_C15_THEME_DARK = 'dark'
_C15_THEME_API_VERSION = 1


def _c15_theme_qt_value(obj, name, default=None):
    """PythonQt에서 메서드 또는 속성으로 노출되는 값을 안전하게 읽는다."""
    if obj is None:
        return default
    try:
        value = getattr(obj, name)
        return value() if callable(value) else value
    except Exception:
        return default


def _c15_theme_detect_fontlab_mode():
    """글립 캔버스가 아닌 QApplication 전역 팔레트로 UI 모드를 판별한다."""
    try:
        app = _C15_THEME_QT_GUI.QApplication.instance()
        palette = _c15_theme_qt_value(app, 'palette')
        if palette is None:
            return _C15_THEME_LIGHT
        window_color = palette.color(_C15_THEME_QT_GUI.QPalette.Window)
        lightness = _c15_theme_qt_value(window_color, 'lightness')
        if lightness is not None and int(lightness) < 128:
            return _C15_THEME_DARK
    except Exception:
        pass
    return _C15_THEME_LIGHT


def _c15_theme_checkbox_qss(theme_mode):
    """Delta Filter 옵션의 모드별 글자색을 반환한다."""
    if theme_mode == _C15_THEME_DARK:
        return "font-size: 11px; padding-left: 10px; color: #E6EDF3;"
    return "font-size: 11px; padding-left: 10px;"


def _c15_theme_apply_button_qss(theme_mode):
    """Apply 버튼의 모드별 스타일을 반환한다."""
    if theme_mode == _C15_THEME_DARK:
        return """
            QPushButton {
                font-size: 14px;
                padding: 5px;
                font-weight: bold;
                background-color: #353A40;
                color: #F2F4F6;
                border: 1px solid #69727D;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #454C54;
                border: 1px solid #87919C;
            }
            QPushButton:pressed {
                background-color: #22272D;
                border: 1px solid #9AA5B1;
            }
        """
    return """
            QPushButton {
                font-size: 14px;
                padding: 5px;
                font-weight: bold;
            }
        """


def _c15_theme_swatch_border(theme_mode):
    """스와치 RGB는 유지하고 테두리만 모드에 맞춰 반환한다."""
    if theme_mode == _C15_THEME_DARK:
        return '#B8C2CC'
    return '#AAA'

# 세 색상 스크립트가 같은 UI 스레드에서 색상 적용 함수로 중첩 진입하는 것을
# 막기 위한 의도적인 공통 플래그다. 컨트롤러나 창 객체는 공유하지 않는다.
_DALGAS_LINKED_COLOR_BUSY_ATTR = '_dalgas_linked_color_operation_busy'


# ── [DEBUG] Delta Filter shape 매칭 진단 스위치 ──────────────────────────────
# True로 두면 _color15_find_all_linked_shapes()가 Delta Filter shape를 만날 때마다
# shapeData ID 조회 과정을 콘솔에 상세히 출력한다.
# 원인이 확정되어(own.shapeData가 필터별 별도 ID를 가짐) 기본값은 False로 둔다.
_C15_DEBUG_DELTA_MATCH = False

# 색상 팔레트 정의
_C15_COLORS = {
    'Black': QtGui.QColor(0, 0, 0, 255),
    'Red': QtGui.QColor(255, 0, 0, 255),
    'Blue': QtGui.QColor(0, 0, 255, 255),
    'Pink': QtGui.QColor(255, 0, 255, 255),  # Magenta
    'Orange': QtGui.QColor(255, 165, 0, 255),
    # 새로운 색상들
    'Green': QtGui.QColor(0, 94, 32, 255),
    'Dark Green': QtGui.QColor(0, 49, 42, 255),
    'Brown': QtGui.QColor(125, 73, 0, 255),
    'Dark Brown': QtGui.QColor(121, 0, 0, 255),
    'Violet': QtGui.QColor(146, 39, 143, 255),
    'Dark Violet': QtGui.QColor(75, 0, 73, 255),
    'Hanul': QtGui.QColor(0, 175, 233, 255),
    'Dark Hanul': QtGui.QColor(0, 118, 163, 255),
    'Blue2': QtGui.QColor(55, 55, 170, 255),
    'Dark Blue': QtGui.QColor(27, 20, 100, 255)
}


def _color15_has_delta_filter(shape):
    """Shape에 Delta Filter가 적용되어 있는지 확인한다.

    shape.shapeBuilder.title == 'Delta'로 판별한다.
    """
    try:
        if not hasattr(shape, 'shapeBuilder'):
            return False
        builder = shape.shapeBuilder
        if builder is None:
            return False
        if hasattr(builder, 'title'):
            return builder.title == 'Delta'
    except Exception:
        pass
    return False


def _color15_get_shape_data_id(shape):
    """Shape의 shapeData ID를 반환합니다.

    Delta Filter가 적용된 Shape는 필터 적용 시점에 FontLab이 그 Shape
    전용의 새로운 shapeData를 별도로 발급하기 때문에, own.shapeData는
    항상 유효한 값이지만 원본 Element Reference의 공유 ID와는 다르다.
    (실측: 단순 Link shape의 shapeData.id == Delta Filter shape의
    includesList[0].shapeData.id, 이 둘이 서로 같은 그룹임)

    따라서 Delta Filter가 적용된 Shape는 own.shapeData를 무시하고,
    Element 패널에 표시되는 원본 Shape(shape.includesList[0])의
    shapeData ID를 무조건 사용해야 같은 Element Reference를 공유하는
    다른 Linked Shape들과 동일한 ID로 매칭된다.
    """
    if _color15_has_delta_filter(shape):
        try:
            if hasattr(shape, 'includesList') and shape.includesList:
                source_shape = shape.includesList[0]
                if hasattr(source_shape, 'shapeData') and source_shape.shapeData:
                    return source_shape.shapeData.id
        except Exception:
            pass
        return None

    try:
        if hasattr(shape, 'shapeData') and shape.shapeData:
            return shape.shapeData.id
    except:
        pass

    return None


def _color15_find_all_linked_shapes(font, shape_data_id, layer_name):
    """
    폰트 전체에서 동일한 shapeData ID를 가진 모든 shapes를 찾습니다.
    
    Args:
        font: pFont 객체
        shape_data_id: 찾을 shapeData ID
        layer_name: 레이어 이름
    
    Returns:
        list of (glyph_name, shape) tuples
    """
    linked_shapes = []
    
    # 모든 글리프 순회
    for glyph in font.pGlyphs():
        try:
            # 해당 레이어의 shapes 가져오기
            shapes = glyph.shapes(layer_name)
            
            # shapes가 None이면 건너뛰기 (빈 글리프 또는 제어 문자)
            if shapes is None:
                continue
            
            for shape in shapes:
                # ── [DEBUG] Delta Filter shape 진단 출력 ──────────────────
                # 원인 파악을 위한 임시 진단 코드. 문제 해결 후 제거 예정.
                if _C15_DEBUG_DELTA_MATCH and _color15_has_delta_filter(shape):
                    try:
                        has_includes = hasattr(shape, 'includesList')
                        includes_len = len(shape.includesList) if has_includes and shape.includesList else 0
                        own_sd = None
                        try:
                            if hasattr(shape, 'shapeData') and shape.shapeData:
                                own_sd = shape.shapeData.id
                        except Exception as e_own:
                            own_sd = f'ERROR({e_own})'
                        inner_sd = None
                        if has_includes and includes_len > 0:
                            try:
                                inner_shape = shape.includesList[0]
                                if hasattr(inner_shape, 'shapeData') and inner_shape.shapeData:
                                    inner_sd = inner_shape.shapeData.id
                                else:
                                    inner_sd = '(includesList[0]에 shapeData 없음)'
                            except Exception as e_inner:
                                inner_sd = f'ERROR({e_inner})'
                        resolved_id = _color15_get_shape_data_id(shape)
                        print(
                            f"[DEBUG-Delta] Glyph:{glyph.name} "
                            f"own.shapeData.id={own_sd} "
                            f"includesList_len={includes_len} "
                            f"includesList[0].shapeData.id={inner_sd} "
                            f"_color15_get_shape_data_id()={resolved_id} "
                            f"target={shape_data_id} "
                            f"MATCH={resolved_id == shape_data_id}"
                        )
                    except Exception as e_dbg:
                        print(f"[DEBUG-Delta] Glyph:{glyph.name} 진단 중 오류: {e_dbg}")
                # ── [DEBUG] 끝 ────────────────────────────────────────────

                # shapeData ID 비교
                if _color15_get_shape_data_id(shape) == shape_data_id:
                    linked_shapes.append((glyph.name, shape))
        except:
            continue
    
    return linked_shapes


def _color15_change_linked_shapes_color(color_name, include_delta=False):
    """C15 색상 적용의 중첩 진입을 막고 실제 작업을 실행한다."""
    if getattr(sys, _DALGAS_LINKED_COLOR_BUSY_ATTR, False):
        print("다른 Linked Element Color 작업이 진행 중입니다.")
        return

    setattr(sys, _DALGAS_LINKED_COLOR_BUSY_ATTR, True)
    try:
        return _color15_change_linked_shapes_color_unlocked(
            color_name, include_delta=include_delta
        )
    finally:
        setattr(sys, _DALGAS_LINKED_COLOR_BUSY_ATTR, False)


def _color15_change_linked_shapes_color_unlocked(color_name, include_delta=False):
    """
    선택된 shape와 Element Reference로 연결된 모든 shapes의 색상을 변경합니다.

    Args:
        color_name: _C15_COLORS에 정의된 색상 이름
        include_delta: True이면 Delta Filter가 적용된 Shape의 색상도 함께 변경한다.
                        (기본값 False: Delta Filter가 적용된 Shape는 Skip)
    """
    # 현재 글리프
    glyph = pGlyph()
    # fgGlyph 객체는 유효해도 bool() 컨텍스트에서 False를 반환하므로
    # 반드시 is not None으로 비교한다.
    if glyph is None:
        print("ERROR: No glyph active!")
        return
    
    # 현재 폰트
    font = pFont()
    if font is None:
        print("ERROR: No font active!")
        return
    
    # 색상 가져오기
    color = _C15_COLORS.get(color_name)
    if not color:
        print(f"ERROR: Unknown color: {color_name}")
        return
    
    # 레이어 이름 먼저 가져오기
    layer_name = glyph.layer().name
    
    # 선택된 shapes 가져오기
    # 방법 1: selectedShapes() - Contour Tool로 노드 선택한 경우
    selected_shapes = glyph.selectedShapes()
    
    # 방법 2: active/selected 속성 체크 - Element Tool로 shape 전체 선택한 경우
    if not selected_shapes:
        all_shapes = glyph.shapes(layer_name)
        selected_shapes = [s for s in all_shapes if (hasattr(s, 'active') and s.active) or (hasattr(s, 'selected') and s.selected)]
    
    if not selected_shapes:
        print("No shapes selected! Please select shapes with Element tool (Q) or Contour tool (V).")
        return
    
    # 각 선택된 shape에 대해 처리
    total_changed = 0
    processed_ids = set()  # 중복 처리 방지
    
    for selected_shape in selected_shapes:
        # shapeData ID 가져오기
        shape_data_id = _color15_get_shape_data_id(selected_shape)
        
        if shape_data_id is None:
            # Delta Filter가 적용된 standalone shape는 옵션에 따라 Skip
            if not include_delta and _color15_has_delta_filter(selected_shape):
                continue
            # standalone shape인 경우 그냥 색상만 변경
            selected_shape.brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
            # Delta Filter 원본 Shape(Element 패널에 표시되는 원본)도 함께 변경
            if include_delta and _color15_has_delta_filter(selected_shape):
                try:
                    if selected_shape.includesList:
                        selected_shape.includesList[0].brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                except Exception:
                    pass
            total_changed += 1
            continue
        
        # 이미 처리한 ID는 건너뛰기
        if shape_data_id in processed_ids:
            continue
        
        processed_ids.add(shape_data_id)
        
        # 동일한 shapeData ID를 가진 모든 shapes 찾기
        linked_shapes = _color15_find_all_linked_shapes(font, shape_data_id, layer_name)
        
        # 모든 linked shapes의 색상 변경
        for glyph_name, shape in linked_shapes:
            # Delta Filter가 적용된 Shape는 옵션에 따라 Skip
            if not include_delta and _color15_has_delta_filter(shape):
                continue
            try:
                shape.brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                # Delta Filter 원본 Shape(Element 패널에 표시되는 원본)도 함께 변경
                if include_delta and _color15_has_delta_filter(shape):
                    try:
                        if shape.includesList:
                            shape.includesList[0].brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                    except Exception:
                        pass
                total_changed += 1
            except Exception as e:
                print(f"ERROR: Failed to apply color to '{glyph_name}': {e}")
        
        # 각 글리프 업데이트
        updated_glyphs = set([glyph_name for glyph_name, _ in linked_shapes])
        for glyph_name in updated_glyphs:
            try:
                g = font.glyph(glyph_name)
                if g:
                    g.update()
                    # 강제로 글리프 업데이트 플래그 설정
                    g.setChanged()
            except:
                pass
    
    # 현재 글리프 업데이트
    glyph.update()
    
    # TypeRig의 updateObject로 강제 업데이트
    try:
        font.updateObject(glyph.fl, 'Color changed', verbose=False)
    except:
        pass
    
    # 선택 상태를 토글하여 캔버스 강제 리프레시
    try:
        # 현재 선택된 shapes 저장
        temp_selected = []
        for shape in selected_shapes:
            if hasattr(shape, 'selected'):
                temp_selected.append(shape)
                shape.selected = False  # 선택 해제
        
        # 글리프 업데이트
        glyph.update()
        
        # 다시 선택
        for shape in temp_selected:
            shape.selected = True
        
        glyph.update()
    except Exception as e:
        print(f"Selection toggle warning: {e}")
    
    # 캔버스 강제 업데이트
    try:
        canvas = fl6.CurrentCanvas()
        if canvas:
            canvas.update()
            canvas.repaint()
    except:
        pass


class C15LinkedColorDialog(QtGui.QDialog):
    """색상 선택 다이얼로그"""
    
    def __init__(self):
        # parent=None: 독립 창으로 생성한다.
        # main_win을 parent로 지정하면 Qt의 parent-child 소유권과
        # Python의 참조가 충돌하여 FontLab 종료 시 SIGSEGV가 발생한다.
        # 또한 _color15_show_color_menu()의 지역 변수 dialog가 함수 종료 후 GC되는 시점에
        # Qt parent의 소유권과 이중 충돌이 발생하므로 반드시 parent=None이어야 한다.
        super(C15LinkedColorDialog, self).__init__(None)
        self._c15_theme_mode = _c15_theme_detect_fontlab_mode()
        self._c15_theme_api_version = _C15_THEME_API_VERSION
        self.setWindowTitle('%s %s' % (_C15_APP_NAME, _C15_APP_VERSION))
        self.setObjectName('dalgas_c15_linked_color_dialog')
        self.setFixedWidth(260)
        
        # parent=None이므로 WindowStaysOnTopHint로 폰트랩 위에 유지한다.
        # WA_DeleteOnClose=False: Python global 변수가 참조하는 동안
        # Qt가 먼저 delete하지 않도록 한다.
        self.setWindowFlags(
            (self.windowFlags()
             | QtCore.Qt.WindowStaysOnTopHint
             | QtCore.Qt.CustomizeWindowHint)
            & ~QtCore.Qt.WindowContextHelpButtonHint
        )
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, False)
        
        self.selected_color = None  # 현재 선택된 색상
        
        # 메인 레이아웃
        main_layout = QtGui.QVBoxLayout()
        # v1.15: 여백/간격을 OS 기본값에 맡기지 않고 명시적으로 고정한다.
        # (macOS의 QMacStyle 기본 여백/간격이 Windows의 QWindowsStyle과 달라
        # 색상 버튼 3등분 정렬이 어긋나고 Apply 버튼 아래 여백이 없어지는
        # 문제가 있었다.)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)
        
        # Delta Filter 옵션
        label_layout = QtGui.QHBoxLayout()

        self.chk_include_delta = QtGui.QCheckBox("Delta Filter가 적용된 Shape 포함")
        # 기본값은 미체크(Delta Filter 적용 Shape 제외)
        self.chk_include_delta.setChecked(False)
        self.chk_include_delta.setStyleSheet(
            _c15_theme_checkbox_qss(self._c15_theme_mode)
        )
        label_layout.addWidget(self.chk_include_delta)

        label_layout.addStretch()
        main_layout.addLayout(label_layout)
        
        # 전체 색상 (한 줄에 3개씩 배치)
        self.color_buttons = {}

        all_color_names = [
            'Red', 'Pink', 'Orange',
            'Hanul', 'Dark Hanul', 'Black',
            'Blue', 'Blue2', 'Dark Blue',
            'Green', 'Dark Green', 'Violet',
            'Brown', 'Dark Brown', 'Dark Violet'
        ]

        COLORS_PER_ROW = 3
        for i in range(0, len(all_color_names), COLORS_PER_ROW):
            row_layout = QtGui.QHBoxLayout()
            # v1.15: 행마다 버튼 간격을 명시적으로 고정하여 macOS/Windows에서
            # 동일하게 렌더링되도록 함(3열 정렬 "이빨" 어긋남 방지).
            row_layout.setSpacing(6)
            # v1.16: 하위 레이아웃(row_layout)의 여백은 Qt 문서상 스타일(QStyle)
            # 기본값을 따르며 OS별로 다를 수 있다. main_layout에 직접 addWidget된
            # Apply 버튼과 너비를 정확히 맞추기 위해 여백을 0으로 명시 고정한다.
            row_layout.setContentsMargins(0, 0, 0, 0)
            for color_name in all_color_names[i:i + COLORS_PER_ROW]:
                btn = self.create_color_button(color_name)
                self.color_buttons[color_name] = btn
                # stretch=1: 버튼이 창 너비에 비례하여 균등하게 확장되도록 한다.
                row_layout.addWidget(btn, 1)
            main_layout.addLayout(row_layout)

        # Apply 버튼 (전체 가로 너비 차지, 높이는 기존 대비 약 50% 수준으로 축소)
        apply_btn = QtGui.QPushButton("Apply")
        apply_btn.setStyleSheet(
            _c15_theme_apply_button_qss(self._c15_theme_mode)
        )
        apply_btn.clicked.connect(self.on_apply)
        main_layout.addWidget(apply_btn)
        
        self.setLayout(main_layout)

        # 창 시작 위치 고정 (QHD 모니터 기준)
        # 오른쪽 패널 열(View Shape Coordinates, Dalgas Paste 등)과 같은 x축에 정렬,
        self.move(1972, 571)

        # ── FontLab 종료 감지: aboutToQuit 시그널 연결 ──────────────────────
        # Qt 정상 종료 경로에서 발화한다. 다중 폰트 오픈 후 종료 시에는
        # 발화하지 않을 수 있으므로 _exit_timer로 병행 감지한다.
        self._runtime_active = False

        # 종료 감지 전용 타이머 (2000ms 저주파 — UI 부하 최소화)
        self._exit_timer = QtCore.QTimer(self)
        self._activate_runtime()

    def _activate_runtime(self):
        """숨겨진 기존 창을 다시 표시할 때 종료 감시 연결을 복구한다."""
        if self._runtime_active:
            return
        try:
            app = QtGui.QApplication.instance()
            if app is not None:
                app.aboutToQuit.connect(self.close)
        except Exception:
            pass
        try:
            self._exit_timer.timeout.connect(self._check_fontlab_alive)
        except Exception:
            pass
        self._exit_timer.start(2000)
        self._runtime_active = True

    # - FontLab 종료 감지 전용 타이머 콜백 --------------------------------
    def _check_fontlab_alive(self):
        """FontLab 종료 감지 전용 타이머 콜백"""
        # [방어코드1] 창/위젯 파괴 과도기에는 즉시 멈춘다
        if not _is_alive(self):
            try:
                self._exit_timer.stop()
            except Exception:
                pass
            return
        try:
            _font_check = fl6.CurrentFont()
        except Exception:
            _font_check = None
        if _font_check is None:
            try:
                _font_count = legacy.fl.count
            except Exception:
                _font_count = 0
            if _font_count > 0:
                return  # 과도기 → 대기
            self._exit_timer.stop()
            try:
                p = self.parent()
                if p is not None:
                    p.close()
                else:
                    self.close()
            except Exception:
                pass

    def create_color_button(self, color_name):
        """색상 버튼 생성"""
        btn = QtGui.QPushButton("")  # 버튼 내 텍스트 라벨 제거 (색상만으로 구분)
        btn.setToolTip(color_name)  # 마우스 오버 시 색상 이름 표시
        btn.setCheckable(True)  # 토글 가능하게
        btn.clicked.connect(lambda checked, name=color_name: self.on_color_selected(name, btn)) # 버튼 객체를 인수로 전달
        
        # 버튼이 창 너비에 비례하여 가로로 확장되도록 SizePolicy 설정
        # (min-width 고정값을 제거하고 Expanding으로 대체 → 3열 배치에서 창 너비에 맞춰 균등 분할)
        btn.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        # v1.15: macOS 네이티브 QPushButton의 sizeHint()가 자체적으로 갖는
        # 최소폭 하한선을 0으로 눌러, Expanding 정책이 3등분을 정확히
        # 계산하도록 함(macOS에서만 버튼 너비가 불균일하고 행 간 "이빨"이
        # 어긋나던 문제의 원인).
        btn.setMinimumWidth(0)
        # v1.15: Fixed 정책에 실제 고정 높이값을 부여하여, 높이도 OS 기본
        # sizeHint에 좌우되지 않고 두 OS에서 동일하게 렌더링되도록 함.
        btn.setFixedHeight(32)
        
        # 버튼 색상 미리보기 및 기본 스타일
        color = _C15_COLORS[color_name]
        text_color = "white" if (color.red() + color.green() + color.blue()) < 384 else "black"
        
        # 기본 스타일 저장 (선택 해제 시 사용) - 얇은 테두리 1px, 모서리를 살짝 둥글게(border-radius)
        # 높이를 기존 대비 80% 수준으로 줄이기 위해 상하 padding을 10px→6px로 축소
        base_border_style = (
            'border: 1px solid %s;'
            % _c15_theme_swatch_border(self._c15_theme_mode)
        )
        btn.setProperty('base_border_style', base_border_style)
        btn.setProperty(
            'base_style',
            f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); "
            f"color: {text_color}; font-weight: bold; padding: 6px 4px; "
            f"{base_border_style} border-radius: 6px;"
        )
        
        btn.setStyleSheet(btn.property('base_style')) # 초기 적용
        
        return btn
    
    def closeEvent(self, event):
        # aboutToQuit 시그널 연결을 해제하여 중복 호출을 방지한다.
        try:
            QtGui.QApplication.instance().aboutToQuit.disconnect(self.close)
        except Exception:
            pass
        try:
            self._exit_timer.stop()
            self._exit_timer.timeout.disconnect()
        except Exception:
            pass
        self._runtime_active = False
        event.accept()

    def __del__(self):
        # Qt가 closeEvent를 호출하지 않고 위젯을 직접 소멸시키는 경우를 방어한다.
        try:
            self._exit_timer.stop()
        except Exception:
            pass

    def close_dialog(self):
        """다이얼로그 닫기"""
        self.close()
    
    def on_color_selected(self, color_name, clicked_btn):
        """색상이 선택되었을 때"""
        
        # 1. 모든 버튼의 테두리 초기화 (선택 해제)
        for name, btn in self.color_buttons.items():
            # 기존 체크 해제
            btn.setChecked(False)
            
            # 기본 스타일로 복원 (테두리 얇게)
            btn.setStyleSheet(btn.property('base_style'))

        # 2. 현재 클릭된 버튼을 항상 선택 상태로 설정
        clicked_btn.setChecked(True)
        
        # 선택된 버튼의 기본 스타일에 아주 굵은 테두리 (5px) 추가
        base_style = clicked_btn.property('base_style')
        
        # 기본 오렌지 테두리, 밝은색은 검은색 테두리
        if color_name in ['Orange', 'Red', 'Pink']:
            border_color = "#000"  # Black
        else:
            border_color = "#FFA500"  # Orange
        
        # 기존 border: 1px solid #AAA; 대신 굵은 테두리 적용
        base_border_style = clicked_btn.property('base_border_style')
        selected_style = base_style.replace(
            base_border_style,
            f"border: 5px solid {border_color};"
        ).replace("padding: 6px 4px;", "padding: 2px 0px;")
        
        clicked_btn.setStyleSheet(selected_style)
        
        self.selected_color = color_name
    
    def on_apply(self):
        """Apply 버튼을 눌렀을 때"""
        if self.selected_color:
            include_delta = self.chk_include_delta.isChecked()
            _color15_change_linked_shapes_color(self.selected_color, include_delta=include_delta)
        else:
            print("Please select a color first!")


_C15_DIALOG_ANCHOR_ATTR = '_dalgas_c15_linked_color_dialog_controller'
_c15_dialog = None

def _color15_show_color_menu():
    """색상 선택 메뉴 표시"""
    global _c15_dialog
    existing = getattr(sys, _C15_DIALOG_ANCHOR_ATTR, None)
    if existing is None:
        existing = _c15_dialog

    # v1.19 이전 창에는 테마 API 표식이 없다. 같은 FontLab 세션에서 새 파일을
    # 실행해도 옛 UI를 재사용하지 않도록 이전 C15 창만 정상 close한다.
    if (existing is not None
            and getattr(existing, '_c15_theme_api_version', None)
            != _C15_THEME_API_VERSION):
        try:
            existing.close()
        except Exception:
            pass
        existing = None
        try:
            setattr(sys, _C15_DIALOG_ANCHOR_ATTR, None)
        except Exception:
            pass

    # 살아있는 기존 인스턴스는 숨김 여부와 무관하게 재활성화한다.
    # deleteLater() 직후 새 창을 만드는 교체 패턴은 사용하지 않는다.
    try:
        if existing is not None and _is_alive(existing):
            existing._activate_runtime()
            existing.show()
            existing.raise_()
            existing.activateWindow()
            _c15_dialog = existing
            setattr(sys, _C15_DIALOG_ANCHOR_ATTR, existing)
            return
    except Exception:
        pass

    _c15_dialog = C15LinkedColorDialog()
    setattr(sys, _C15_DIALOG_ANCHOR_ATTR, _c15_dialog)
    _c15_dialog.show()


# 메인 실행
if __name__ == '__main__':
    _color15_show_color_menu()
