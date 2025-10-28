#FLM: Cluade: Change Linked Element Color
# -*- coding: utf-8 -*-

"""
FontLab 8 Script: Element Reference로 연결된 shapes의 색상을 동시에 변경
선택한 shape와 동일한 Element Reference를 가진 모든 shapes의 Fill Color를 변경합니다.

작동 방식:
1. 현재 글리프에서 shape를 선택
2. 색상을 선택
3. 선택한 shape의 shapeData ID를 찾음
4. 폰트 전체에서 동일한 shapeData ID를 가진 모든 shapes를 찾아 색상 변경
"""

__version__ = "1.0"

import fontlab as fl6
from typerig.proxy.fl.objects.glyph import pGlyph
from typerig.proxy.fl.objects.font import pFont
from typerig.proxy.fl.gui import QtGui
from PythonQt import QtCore

# 색상 팔레트 정의
COLORS = {
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
    'Blue2': QtGui.QColor(48, 50, 140, 255),
    'Dark Blue': QtGui.QColor(27, 20, 100, 255)
}


def get_shape_data_id(shape):
    """Shape의 shapeData ID를 반환합니다."""
    try:
        if hasattr(shape, 'shapeData') and shape.shapeData:
            return shape.shapeData.id
    except:
        pass
    return None


def find_all_linked_shapes(font, shape_data_id, layer_name):
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
            
            for shape in shapes:
                # shapeData ID 비교
                if get_shape_data_id(shape) == shape_data_id:
                    linked_shapes.append((glyph.name, shape))
        except Exception as e:
            print(f"Warning: Error processing glyph {glyph.name}: {e}")
            continue
    
    return linked_shapes


def change_linked_shapes_color(color_name):
    """
    선택된 shape와 Element Reference로 연결된 모든 shapes의 색상을 변경합니다.
    """
    # 현재 글리프
    glyph = pGlyph()
    if not glyph:
        print("ERROR: No glyph active!")
        return
    
    # 현재 폰트
    font = pFont()
    if not font:
        print("ERROR: No font active!")
        return
    
    # 색상 가져오기
    color = COLORS.get(color_name)
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
        shape_data_id = get_shape_data_id(selected_shape)
        
        if shape_data_id is None:
            print(f"Warning: Selected shape has no shapeData ID (standalone shape)")
            # standalone shape인 경우 그냥 색상만 변경
            selected_shape.brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
            total_changed += 1
            continue
        
        # 이미 처리한 ID는 건너뛰기
        if shape_data_id in processed_ids:
            continue
        
        processed_ids.add(shape_data_id)
        
        # 동일한 shapeData ID를 가진 모든 shapes 찾기
        linked_shapes = find_all_linked_shapes(font, shape_data_id, layer_name)
        
        print(f"\nShape Data ID: {shape_data_id}")
        print(f"Found {len(linked_shapes)} linked shapes:")
        
        # 모든 linked shapes의 색상 변경
        for glyph_name, shape in linked_shapes:
            try:
                shape.brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)
                total_changed += 1
                print(f"  - {glyph_name}")
            except Exception as e:
                print(f"  - {glyph_name} (ERROR: {e})")
        
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
    
    print(f"\n{color_name}: Changed {total_changed} shape(s) across {len(processed_ids)} element reference(s)")


class ColorDialog(QtGui.QDialog):
    """색상 선택 다이얼로그"""
    
    def __init__(self):
        super(ColorDialog, self).__init__()
        self.setWindowTitle("Change Linked Shapes Color")
        self.setMinimumWidth(600)
        
        # Always on Top 설정
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        
        self.selected_color = None  # 현재 선택된 색상
        
        # 메인 레이아웃
        main_layout = QtGui.QVBoxLayout()
        
        # 설명 라벨
        label = QtGui.QLabel("Select color for linked shapes:")
        main_layout.addWidget(label)
        
        # 기본 색상 (5개)
        basic_layout = QtGui.QHBoxLayout()
        self.color_buttons = {}
        
        for color_name in ['Black', 'Red', 'Blue', 'Pink', 'Orange']:
            btn = self.create_color_button(color_name)
            self.color_buttons[color_name] = btn
            basic_layout.addWidget(btn)
        
        main_layout.addLayout(basic_layout)
        
        # 구분선 추가
        separator = QtGui.QFrame()
        separator.setFrameShape(QtGui.QFrame.HLine)
        separator.setFrameShadow(QtGui.QFrame.Sunken)
        separator.setLineWidth(2)
        main_layout.addWidget(separator)
        
        # 추가 색상 (5열 x 2행)
        # 첫 번째 행 (밝은 색)
        light_row = QtGui.QHBoxLayout()
        for color_name in ['Green', 'Brown', 'Violet', 'Hanul', 'Blue2']:
            btn = self.create_color_button(color_name)
            self.color_buttons[color_name] = btn
            light_row.addWidget(btn)
        
        main_layout.addLayout(light_row)
        
        # 두 번째 행 (어두운 색)
        dark_row = QtGui.QHBoxLayout()
        for color_name in ['Dark Green', 'Dark Brown', 'Dark Violet', 'Dark Hanul', 'Dark Blue']:
            btn = self.create_color_button(color_name)
            self.color_buttons[color_name] = btn
            dark_row.addWidget(btn)
        
        main_layout.addLayout(dark_row)
        
        # Apply와 Close 버튼을 담을 수평 레이아웃
        button_layout = QtGui.QHBoxLayout()
        
        # Apply 버튼
        apply_btn = QtGui.QPushButton("Apply")
        apply_btn.clicked.connect(self.on_apply)
        button_layout.addWidget(apply_btn)
        
        # Close 버튼
        close_btn = QtGui.QPushButton("Close")
        close_btn.clicked.connect(self.close_dialog)
        button_layout.addWidget(close_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_color_button(self, color_name):
        """색상 버튼 생성"""
        btn = QtGui.QPushButton(color_name)
        btn.setCheckable(True)  # 토글 가능하게
        btn.clicked.connect(lambda checked, name=color_name: self.on_color_selected(name))
        
        # 버튼 색상 미리보기
        color = COLORS[color_name]
        # 어두운 색은 흰색 텍스트, 밝은 색은 검은색 텍스트
        text_color = "white" if (color.red() + color.green() + color.blue()) < 384 else "black"
        btn.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); color: {text_color}; font-weight: bold; padding: 10px; min-width: 80px;")
        
        return btn
    
    def close_dialog(self):
        """다이얼로그 닫기"""
        self.close()
    
    def on_color_selected(self, color_name):
        """색상이 선택되었을 때"""
        # 이전에 선택된 버튼 해제
        for name, btn in self.color_buttons.items():
            if name != color_name:
                btn.setChecked(False)
        
        # 현재 선택된 색상 저장
        self.selected_color = color_name
        print(f"Selected: {color_name}")
    
    def on_apply(self):
        """Apply 버튼을 눌렀을 때"""
        if self.selected_color:
            change_linked_shapes_color(self.selected_color)
        else:
            print("Please select a color first!")


def show_color_menu():
    """색상 선택 메뉴 표시"""
    dialog = ColorDialog()
    dialog.show()


# 메인 실행
if __name__ == '__main__':
    show_color_menu()
