import os
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
from PIL import Image, ImageFilter
import time

app = Flask(__name__)

# Define the directory where your original images are stored
image_dir = 'static/images/output'

# Define the directory where thumbnails will be stored
thumbnail_dir = 'static/thumbnails'

# Ensure directories exist
os.makedirs(image_dir, exist_ok=True)
os.makedirs(thumbnail_dir, exist_ok=True)

@app.route('/')
def image_gallery():
    
    valid_image_files = [f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.png', '.jpeg', '.gif'))]
    
   
    valid_image_files.sort(key=lambda x: os.path.getmtime(os.path.join(image_dir, x)), reverse=True)

    # Safely convert 'page' to an integer, defaulting to 1 if invalid or not provided
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1 # Default to page 1 if 'page' parameter is not a valid integer

    images_per_page_gallery = 100 
    total_pages = (len(valid_image_files) + images_per_page_gallery - 1) // images_per_page_gallery

   
    available_width = request.args.get('browser_width', type=int, default=1200)

    max_columns = min(available_width // 220, 5)

   
    start_idx = (page - 1) * images_per_page_gallery
    end_idx = start_idx + images_per_page_gallery


    current_images = valid_image_files[start_idx:end_idx]

    
    generate_thumbnails(current_images)

    return render_template('index.html', current_thumbnails=current_images, total_pages=total_pages, page=page)

def generate_thumbnails(image_list):
    for image_filename in image_list:
        thumbnail_path = os.path.join(thumbnail_dir, image_filename)
        original_image_path = os.path.join(image_dir, image_filename)

        if not os.path.exists(original_image_path):
            print(f"Original image not found for thumbnail generation: {original_image_path}")
            continue

      
        if not os.path.exists(thumbnail_path) or \
           os.path.getmtime(original_image_path) > os.path.getmtime(thumbnail_path):
            try:
             
                with Image.open(original_image_path) as original_image:
                    
                    original_image.thumbnail((200, 200), Image.Resampling.LANCZOS)
                    original_image.save(thumbnail_path)
            except Exception as e:
                print(f"Error generating thumbnail for {image_filename}: {str(e)}")



@app.route('/api/images', methods=['GET'])
def get_all_images():
    try:
        
        all_files_in_dir = os.listdir(image_dir)
        images_data = []
        for filename in all_files_in_dir:
            file_path = os.path.join(image_dir, filename)
           
            if os.path.isdir(file_path):
                continue

            try:
              
                with Image.open(file_path) as img:
                    images_data.append({
                        'filename': filename,
                        'url': url_for('static', filename=f'images/output/{filename}'),
                        'thumbnail_url': url_for('static', filename=f'thumbnails/{filename}'),
                        'size_bytes': os.path.getsize(file_path),
                        'width': img.width,
                        'height': img.height,
                        'format': img.format,
                        'last_modified': os.path.getmtime(file_path) 
                    })
            except Exception as e:
              
                print(f"Could not read image metadata for {filename}: {e}")
                images_data.append({
                    'filename': filename,
                    'url': url_for('static', filename=f'images/output/{filename}'),
                    'thumbnail_url': url_for('static', filename=f'thumbnails/{filename}'),
                    'error': str(e),
                    'size_bytes': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    'last_modified': os.path.getmtime(file_path) if os.path.exists(file_path) else 0
                })

        return jsonify(images_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/images', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        filename = file.filename
        file_path = os.path.join(image_dir, filename)
        
       
        if os.path.exists(file_path):
            return jsonify({"error": f"An image with the name '{filename}' already exists. Please rename your file or delete the existing one."}), 409

        try:
            file.save(file_path)
           
            generate_thumbnails([filename])
            return jsonify({"message": "Image uploaded successfully", "filename": filename}), 201
        except Exception as e:
            return jsonify({"error": f"Failed to save image: {str(e)}"}), 500
    return jsonify({"error": "Something went wrong"}), 500


@app.route('/api/images/<filename>', methods=['GET'])
def get_image_details(filename):
    file_path = os.path.join(image_dir, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "Image not found"}), 404

    try:
       
        with Image.open(file_path) as img:
            return jsonify({
                'filename': filename,
                'url': url_for('static', filename=f'images/output/{filename}'),
                'thumbnail_url': url_for('static', filename=f'thumbnails/{filename}'),
                'size_bytes': os.path.getsize(file_path),
                'width': img.width,
                'height': img.height,
                'format': img.format,
                'last_modified': os.path.getmtime(file_path)
            }), 200
    except Exception as e:
       
        return jsonify({"error": f"Could not read image details: {str(e)}"}), 500


@app.route('/api/images/<old_filename>', methods=['PUT'])
def update_image(old_filename):
    data = request.get_json()
    new_filename = data.get('new_filename')

    if not new_filename:
        return jsonify({"error": "New filename not provided"}), 400

    old_file_path = os.path.join(image_dir, old_filename)
    new_file_path = os.path.join(image_dir, new_filename)

    old_thumbnail_path = os.path.join(thumbnail_dir, old_filename)
    new_thumbnail_path = os.path.join(thumbnail_dir, new_filename)

    if not os.path.exists(old_file_path):
        return jsonify({"error": "Original image not found"}), 404

    if os.path.exists(new_file_path):
        return jsonify({"error": "Image with new filename already exists"}), 409 

    try:
        os.rename(old_file_path, new_file_path)
        if os.path.exists(old_thumbnail_path):
            os.rename(old_thumbnail_path, new_thumbnail_path)
        return jsonify({"message": "Image renamed successfully", "old_filename": old_filename, "new_filename": new_filename}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to rename image: {str(e)}"}), 500


@app.route('/api/images/<filename>', methods=['DELETE'])
def delete_image(filename):
    file_path = os.path.join(image_dir, filename)
    thumbnail_path = os.path.join(thumbnail_dir, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "Image not found"}), 404

    try:
        os.remove(file_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
        return jsonify({"message": "Image deleted successfully", "filename": filename}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete image: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999, debug=True)
