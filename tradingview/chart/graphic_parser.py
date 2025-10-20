"""
图形解析模块
"""

TRANSLATOR = {
    'extend': {
        'r': 'right',
        'l': 'left',
        'b': 'both',
        'n': 'none',
    },
    'yLoc': {
        'pr': 'price',
        'ab': 'abovebar',
        'bl': 'belowbar',
    },
    'labelStyle': {
        'n': 'none',
        'xcr': 'xcross',
        'cr': 'cross',
        'tup': 'triangleup',
        'tdn': 'triangledown',
        'flg': 'flag',
        'cir': 'circle',
        'aup': 'arrowup',
        'adn': 'arrowdown',
        'lup': 'label_up',
        'ldn': 'label_down',
        'llf': 'label_left',
        'lrg': 'label_right',
        'llwlf': 'label_lower_left',
        'llwrg': 'label_lower_right',
        'luplf': 'label_upper_left',
        'luprg': 'label_upper_right',
        'lcn': 'label_center',
        'sq': 'square',
        'dia': 'diamond',
    },
    'lineStyle': {
        'sol': 'solid',
        'dot': 'dotted',
        'dsh': 'dashed',
        'al': 'arrow_left',
        'ar': 'arrow_right',
        'ab': 'arrow_both',
    },
    'boxStyle': {
        'sol': 'solid',
        'dot': 'dotted',
        'dsh': 'dashed',
    },
}

def graphic_parse(raw_graphic=None, indexes=None):
    """
    解析图形数据
    
    Args:
        raw_graphic: 原始图形数据
        indexes: 索引列表
        
    Returns:
        dict: 解析后的图形数据
    """
    if raw_graphic is None:
        raw_graphic = {}
    if indexes is None:
        indexes = []
        
    return {
        'labels': [
            {
                'id': l['id'],
                'x': indexes[l['x']],
                'y': l['y'],
                'yLoc': TRANSLATOR['yLoc'].get(l['yl'], l['yl']),
                'text': l['t'],
                'style': TRANSLATOR['labelStyle'].get(l['st'], l['st']),
                'color': l['ci'],
                'textColor': l['tci'],
                'size': l['sz'],
                'textAlign': l['ta'],
                'toolTip': l['tt'],
            }
            for l in raw_graphic.get('dwglabels', {}).values()
        ],
        
        'lines': [
            {
                'id': l['id'],
                'x1': indexes[l['x1']],
                'y1': l['y1'],
                'x2': indexes[l['x2']],
                'y2': l['y2'],
                'extend': TRANSLATOR['extend'].get(l['ex'], l['ex']),
                'style': TRANSLATOR['lineStyle'].get(l['st'], l['st']),
                'color': l['ci'],
                'width': l['w'],
            }
            for l in raw_graphic.get('dwglines', {}).values()
        ],
        
        'boxes': [
            {
                'id': b['id'],
                'x1': indexes[b['x1']],
                'y1': b['y1'],
                'x2': indexes[b['x2']],
                'y2': b['y2'],
                'color': b['c'],
                'bgColor': b['bc'],
                'extend': TRANSLATOR['extend'].get(b['ex'], b['ex']),
                'style': TRANSLATOR['boxStyle'].get(b['st'], b['st']),
                'width': b['w'],
                'text': b['t'],
                'textSize': b['ts'],
                'textColor': b['tc'],
                'textVAlign': b['tva'],
                'textHAlign': b['tha'],
                'textWrap': b['tw'],
            }
            for b in raw_graphic.get('dwgboxes', {}).values()
        ],
        
        'tables': [
            {
                'id': t['id'],
                'position': t['pos'],
                'rows': t['rows'],
                'columns': t['cols'],
                'bgColor': t['bgc'],
                'frameColor': t['frmc'],
                'frameWidth': t['frmw'],
                'borderColor': t['brdc'],
                'borderWidth': t['brdw'],
                'cells': lambda: get_cells(t['id'], raw_graphic.get('dwgtablecells', {})),
            }
            for t in raw_graphic.get('dwgtables', {}).values()
        ],
        
        'horizLines': [
            {
                **h,
                'startIndex': indexes[h['startIndex']],
                'endIndex': indexes[h['endIndex']],
            }
            for h in raw_graphic.get('horizlines', {}).values()
        ],
        
        'polygons': [
            {
                **p,
                'points': [
                    {
                        **pt,
                        'index': indexes[pt['index']],
                    }
                    for pt in p['points']
                ],
            }
            for p in raw_graphic.get('polygons', {}).values()
        ],
        
        'horizHists': [
            {
                **h,
                'firstBarTime': indexes[h['firstBarTime']],
                'lastBarTime': indexes[h['lastBarTime']],
            }
            for h in raw_graphic.get('hhists', {}).values()
        ],
        
        'raw': lambda: raw_graphic,
    }
    
def get_cells(table_id, cells_data):
    """
    获取表格单元格
    
    Args:
        table_id: 表格ID
        cells_data: 单元格数据
        
    Returns:
        list: 单元格矩阵
    """
    matrix = []
    
    for cell in cells_data.values():
        if cell.get('tid') != table_id:
            continue
            
        row = cell.get('row', 0)
        col = cell.get('col', 0)
        
        # 确保矩阵有足够的行
        while len(matrix) <= row:
            matrix.append([])
        
        # 确保行有足够的列
        while len(matrix[row]) <= col:
            matrix[row].append(None)
        
        # 填充单元格数据
        matrix[row][col] = {
            'id': cell.get('id'),
            'text': cell.get('t', ''),
            'width': cell.get('w', 0),
            'height': cell.get('h', 0),
            'textColor': cell.get('tc', 0),
            'textHAlign': cell.get('tha', 'left'),
            'textVAlign': cell.get('tva', 'top'),
            'textSize': cell.get('ts', 'normal'),
            'bgColor': cell.get('bgc', 0),
        }
    
    return matrix 