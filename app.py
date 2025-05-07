from flask import Flask, render_template, request, send_file, jsonify
import qrcode
from PIL import Image, ImageDraw, ImageOps
from qrcode.constants import ERROR_CORRECT_H
import os
import io

app = Flask(__name__)

class QRCodeGenerator:
    def __init__(self):
        self.qr = qrcode.QRCode(
            version=5,
            error_correction=ERROR_CORRECT_H,
            box_size=10,
            border=4    
        )

    def create_circular_logo(self, logo_image, size):
        mask = Image.new('L', (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)

        logo_image = logo_image.resize((size, size), Image.Resampling.LANCZOS)
        output = ImageOps.fit(logo_image, mask.size, centering=(0.5, 0.5))
        output.putalpha(mask)

        return output

    def generate_qr_code(self, data, fg_color="black", bg_color="white", logo_path=None):
        self.qr.clear()
        self.qr.add_data(data)
        self.qr.make(fit=True)

        qr_image = self.qr.make_image(fill_color=fg_color, back_color=bg_color).convert('RGBA')


        padding = 40
        new_size = (qr_image.size[0] + padding * 2, qr_image.size[1] + padding * 2)
        final_image = Image.new('RGBA', new_size, (0, 0, 0, 0))
        final_image.paste(qr_image, (padding, padding))

        if logo_path:
            try:
                logo = Image.open(logo_path)
                logo_size = int(qr_image.size[0] * 0.25)
                circular_logo = self.create_circular_logo(logo, logo_size)

                bg_size = int(logo_size * 1.1)
                background = Image.new('RGBA', (bg_size, bg_size), 'white')
                bg_mask = Image.new('L', (bg_size, bg_size), 0)
                bg_draw = ImageDraw.Draw(bg_mask)
                bg_draw.ellipse((0, 0, bg_size, bg_size), fill=255)

                pos_bg = ((final_image.size[0] - bg_size) // 2,
                          (final_image.size[1] - bg_size) // 2)
                pos_logo = ((final_image.size[0] - logo_size) // 2,
                            (final_image.size[1] - logo_size) // 2)

                final_image.paste(background, pos_bg, bg_mask)
                final_image.paste(circular_logo, pos_logo, circular_logo)

            except Exception as e:
                print(f"Error adding logo: {str(e)}")

        img_io = io.BytesIO()
        final_image.save(img_io, 'PNG', quality=95)
        img_io.seek(0)
        return img_io


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate_qr():
    try:
        data = request.form.get('data')
        fg_color = request.form.get('fg_color', 'black')
        bg_color = request.form.get('bg_color', 'white')
        logo = request.files.get('logo')  # ✅ Fixed this line

        logo_path = None
        if logo and logo.filename != '':
            logo_path = 'temp_logo.png'
            logo.save(logo_path)

        generator = QRCodeGenerator()
        img_io = generator.generate_qr_code(
            data,
            fg_color,
            bg_color,
            logo_path
        )

        if logo_path and os.path.exists(logo_path):
            os.remove(logo_path)

        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name='qr_code.png'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)