import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, send_file, abort
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://u357c53148.goho.co"], "methods": ["GET", "POST", "OPTIONS"], "allow_headers": "*"}})
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULT_FOLDER'] = 'static/results'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB限制

# 确保目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    # 设置超时时间为300秒（5分钟）
    request.environ['werkzeug.server.shutdown'] = lambda: None
    request.environ['werkzeug.server.timeout'] = 300
    # 调试输出请求信息
    print("Received request with headers:", request.headers)
    print("Received request with form data:", request.form)
    print("Received request with files:", request.files)
    print("Request started at:", datetime.now())

    # 默认图片路径
    default_image_path = "/Users/liyinchi/workspace/python/haibao/static/uploads/模版-空.jpg"
    
    # 如果用户上传了图片
    if 'image' in request.files and request.files['image'].filename != '':
        image_file = request.files['image']
        if not allowed_file(image_file.filename):
            print("Error: Unsupported file format:", image_file.filename)
            abort(400, '不支持的图片格式')
        
        filename = secure_filename(image_file.filename)
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print("Saving image to:", img_path)
        image_file.save(img_path)
    else:
        # 使用默认图片
        img_path = default_image_path
    
    try:
        img = Image.open(img_path)
        draw = ImageDraw.Draw(img)
        
        # 字体处理
        font_path = None
        if 'font' in request.files:
            font_file = request.files['font']
            if font_file.filename != '':
                font_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                       secure_filename(font_file.filename))
                print("Saving font to:", font_path)
                font_file.save(font_path)
        
         # 字体配置
        font_size = int(request.form.get('size', 40))
        color_value = request.form.get('color', '#FFFFFF')  # 默认白色
        if color_value.startswith('#') or len(color_value) == 6:  # 支持 #RRGGBB 和 RRGGBB 格式
            hex_color = color_value.lstrip('#')
            font_color = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        else:
            # 处理 R,G,B 格式
            font_color = tuple(map(int, color_value.split(',')))
        position = (int(request.form.get('x', 20)), int(request.form.get('y', 20)))
        print("Font settings - size:", font_size, "color:", font_color, "position:", position)
        # 加载字体
        try:
            if font_path:
                font = ImageFont.truetype(font_path, font_size)
            else:
                # 使用指定的默认字体
                default_font_path = "/Users/liyinchi/workspace/python/haibao/font/TaiwanPearl/TaiwanPearl-Medium.ttf"
                font = ImageFont.truetype(default_font_path, font_size)
            
            # 中文验证
            test_text = "中文测试"
            if not font.getmask(test_text).getbbox():
                print("Error: Font does not support Chinese characters")
                return "字体不支持中文", 400

        except Exception as e:
            print("Error loading font:", str(e))
            return f"字体加载失败: {str(e)}", 400

        # 添加文字
        text = request.form.get('text', '')
        if text:
            try:
                if isinstance(text, bytes):
                    text = text.decode('utf-8')
                draw.text(position, text, font=font, fill=font_color, encoding='utf-8')
            except UnicodeEncodeError:
                print("Error: Text encoding error")
                return "文本编码错误，请使用UTF-8编码", 400

        # 添加新字段的文字
        name = request.form.get('name', '')
        profession = request.form.get('profession', '')
        years = request.form.get('years', '')
        rating = request.form.get('rating', '')
        self_evaluation = request.form.get('self_evaluation', '')
        new_text = f"姓名: {name}\n职业: {profession}\n从业年限: {years}年\n评分: {rating}\n自我评价: {self_evaluation}"
        new_position = (position[0], position[1] + 50)  # 调整位置
        draw.text(new_position, new_text, font=font, fill=font_color, encoding='utf-8')

        # 保存结果
        result_filename = f"{uuid.uuid4()}.png"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        print("Saving result image to:", result_path)
        img.save(result_path, 'PNG')
        
        # 清理临时文件（仅清理用户上传的图片）
        if img_path != default_image_path:
            os.remove(img_path)
        if font_path and os.path.exists(font_path):
            os.remove(font_path)

        return send_file(result_path, mimetype='image/png', as_attachment=True)
    
    except Exception as e:
        # 异常处理（仅清理用户上传的图片）
        if img_path != default_image_path and os.path.exists(img_path):
            os.remove(img_path)
        return f"处理失败: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)