**ComfyUI Output Images Gallery - Enhanced with API & Image Management**
This project upgrades a basic Flask image gallery application into a more robust and extensible application for managing ComfyUI output images.


Key Enhancements:
Comprehensive RESTful API:
Full CRUD (Create, Read, Update, Delete) operations for image files, accessible via /api/images.
Uses standard REST principles (HTTP methods, JSON format, proper status codes).
Enables programmatic access for image upload, retrieval of details, renaming, and deletion.

Enhanced Web UI:
Integrated image upload functionality directly into the web interface.
Added a dedicated section for viewing details, renaming, and deleting specific images.
Real-time API response display in the UI for user feedback.

Improved Image Handling:
Automatic thumbnail generation for new images.
Dynamic sorting of images by last modified date (newest first).
Technical Highlights:

Framework: Built with Flask for the web application and API.
Image Processing: Utilizes Pillow (PIL Fork) for creating and managing image thumbnails.
API Design: Clear API endpoints for image management operations.

File System Integration: Direct interaction with the file system for storing and managing images and their thumbnails.

Validation: Basic validation for file types and existence checks for images.
Testing: Includes unit tests using unittest for key functionalities like thumbnail generation and API endpoints.


Setup & Running:
1.  **Clone**:
    ```bash
    git clone [[https://github.com/JmRILKayn/flask-image-gallery.git](https://github.com/JmRILKayn/flask-image-gallery.git)](https://github.com/Smuzzies/comfyui_image_gallery.git)
    cd flask-image-gallery
    ```
2.  **Env**:
    ```bash
    python -m venv venv
    venv\Scripts\activate
    
    ```
3.  **Install**:
    ```bash
    pip install Flask Pillow
    ```
4.  **Run App**:
    ```bash
    python app.py
    ```
    Access the application at `http://0.0.0.0:9999/` or `http://127.0.0.1:9999/`.

5.  **Run Tests**:
    ```bash
    python -m unittest test.py
    ```
    This will execute the unit tests defined in `test.py`.

Repository Links
Original Repository: https://github.com/Smuzzies/comfyui_image_gallery.git
Forked with Enhancements: https://github.com/6shay9/comfyui_image_gallery-modified.git
