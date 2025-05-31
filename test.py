import unittest
import os
import json
import tempfile
import shutil
from PIL import Image # Used for creating dummy images and verifying image properties
import time
import io 
from unittest import mock # For mocking system calls



from app import app, image_dir, thumbnail_dir, generate_thumbnails

class FlaskImageGalleryAPITests(unittest.TestCase):

    def setUp(self):
        """
        Setup performed before each test method.
        This creates a clean, temporary environment for each test.
        """
        
        global image_dir, thumbnail_dir

        
        self.old_image_dir_ref = image_dir
        self.old_thumbnail_dir_ref = thumbnail_dir

        
        self.temp_image_dir = tempfile.mkdtemp()
        self.temp_thumbnail_dir = tempfile.mkdtemp()


        self.image_dir_patch = mock.patch('app.image_dir', self.temp_image_dir)
        self.thumbnail_dir_patch = mock.patch('app.thumbnail_dir', self.temp_thumbnail_dir)

        self.mock_image_dir = self.image_dir_patch.start()
        self.mock_thumbnail_dir = self.thumbnail_dir_patch.start()

        
        app.config['TESTING'] = True
        app.config['DEBUG'] = False

        
        self.client = app.test_client()

    def tearDown(self):
        """
        Teardown performed after each test method.
        This cleans up the temporary directories and restores original global paths.
        """
       
        self.image_dir_patch.stop()
        self.thumbnail_dir_patch.stop()

        
        shutil.rmtree(self.temp_image_dir)
        shutil.rmtree(self.temp_thumbnail_dir)

        
        global image_dir, thumbnail_dir
        image_dir = self.old_image_dir_ref
        thumbnail_dir = self.old_thumbnail_dir_ref

    def create_dummy_image_file(self, directory, filename, size=(100, 100), color=(255, 0, 0)):
        """Helper function to create a dummy image file in the specified directory."""
        filepath = os.path.join(directory, filename)
        # Ensure the target directory exists before saving the image.
        os.makedirs(directory, exist_ok=True)
        img = Image.new('RGB', size, color)
        img.save(filepath)
        return filepath

    

    def test_upload_image_success(self):
        """Test successful image upload (POST /api/images)."""
        # Create a dummy image in a temporary location outside the app's patched image_dir
        
        dummy_filepath = self.create_dummy_image_file(tempfile.gettempdir(), "test_upload.png")
        
        # Open the dummy file in binary read mode to simulate an uploaded file.
        with open(dummy_filepath, 'rb') as f:
            # Send a POST request to the /api/images endpoint with the image file data.
            response = self.client.post('/api/images', data={'image': (f, 'test_upload.png')})
        
        
        self.assertEqual(response.status_code, 201)
        # Parse the JSON response.
        data = json.loads(response.data)
        
        self.assertEqual(data['message'], "Image uploaded successfully")
        self.assertEqual(data['filename'], "test_upload.png")
       
        self.assertTrue(os.path.exists(os.path.join(self.mock_image_dir, "test_upload.png")))
        self.assertTrue(os.path.exists(os.path.join(self.mock_thumbnail_dir, "test_upload.png")))
        
        # Clean up the original dummy file after the upload test.
        os.remove(dummy_filepath)

    def test_upload_image_no_file_provided(self):
        """Test upload when no file is provided in the request (negative case)."""
        # Send a POST request without 
        response = self.client.post('/api/images', data={})
        # Assert the HTTP status code is 400 (Bad Request).
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], "No image file provided")

    def test_upload_image_empty_filename(self):
        """Test upload when a file input is present but with an empty filename (negative case)."""
        # Simulate an empty file upload 
        response = self.client.post('/api/images', data={'image': (io.BytesIO(b''), '')})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], "No selected file")

    def test_upload_image_duplicate_filename_overwrites(self):
        """Test uploading an image with a filename that already exists (current app.py now returns 409)."""
        # Create a dummy image to be uploaded initially.
        dummy_filepath = self.create_dummy_image_file(tempfile.gettempdir(), "duplicate_test.png")
        
        # First upload:
        with open(dummy_filepath, 'rb') as f:
            self.client.post('/api/images', data={'image': (f, 'duplicate_test.png')})

        # Simulate a modification to the file 
        self.create_dummy_image_file(tempfile.gettempdir(), "duplicate_test.png", color=(0, 255, 0))
        
        # Second upload with the same filename:
        with open(dummy_filepath, 'rb') as f:
            response = self.client.post('/api/images', data={'image': (f, 'duplicate_test.png')})
        
        # FIX: Assert that the status code is 409 
        self.assertEqual(response.status_code, 409) 
        data = json.loads(response.data)
        self.assertIn("already exists", data['error']) 
        
        # Clean up the dummy file.
        os.remove(dummy_filepath)

    

    def test_get_all_images_empty(self):
        """Test getting all images when the image directory is empty."""
        response = self.client.get('/api/images')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data, []) 

    def test_get_all_images_with_data(self):
        """Test getting all images when valid images exist in the directory."""
        
        self.create_dummy_image_file(self.mock_image_dir, "img1.jpg")
        self.create_dummy_image_file(self.mock_image_dir, "img2.png")
        
        generate_thumbnails(["img1.jpg", "img2.png"])

        response = self.client.get('/api/images')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2) 
        
        
        filenames = {img['filename'] for img in data}
        self.assertIn("img1.jpg", filenames)
        self.assertIn("img2.png", filenames)
        
        
        img_data = next(item for item in data if item["filename"] == "img1.jpg")
        self.assertIn('url', img_data)
        self.assertIn('thumbnail_url', img_data)
        self.assertIn('size_bytes', img_data)
        self.assertIn('width', img_data)
        self.assertIn('height', img_data)
        self.assertIn('format', img_data)
        self.assertIn('last_modified', img_data)

    def test_get_all_images_with_bad_image(self):
        """Test getting all images when one file exists but is not a valid image."""
        
        self.create_dummy_image_file(self.mock_image_dir, "good_image.png")
        generate_thumbnails(["good_image.png"])

        
        bad_image_path = os.path.join(self.mock_image_dir, "bad_image.txt")
        with open(bad_image_path, "w") as f:
            f.write("This is not an image.")

        response = self.client.get('/api/images')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2) 
        
       
        bad_img_data = next(item for item in data if item["filename"] == "bad_image.txt")
        self.assertIn('error', bad_img_data)
        self.assertIn("cannot identify image file", bad_img_data['error'])

   

    def test_get_image_details_success(self):
        """Test getting details for a specific existing image (GET /api/images/<filename>)."""
       
        self.create_dummy_image_file(self.mock_image_dir, "detail_test.png")
        generate_thumbnails(["detail_test.png"]) 

        response = self.client.get('/api/images/detail_test.png')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['filename'], "detail_test.png")
        self.assertEqual(data['width'], 100)
        self.assertEqual(data['height'], 100)
        self.assertEqual(data['format'], "PNG")
        self.assertIn('url', data)
        self.assertIn('thumbnail_url', data)
        self.assertIn('size_bytes', data)
        self.assertIn('last_modified', data)

    def test_get_image_details_not_found(self):
        """Test getting details for a non-existent image (negative case)."""
        response = self.client.get('/api/images/non_existent.jpg')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], "Image not found")

    def test_get_image_details_bad_image_file(self):
        """Test getting details for a file that exists but is not a valid image (negative case)."""
        
        bad_image_path = os.path.join(self.mock_image_dir, "corrupt.jpg")
        with open(bad_image_path, "w") as f:
            f.write("This is not a real JPEG.")

        response = self.client.get('/api/images/corrupt.jpg')
        self.assertEqual(response.status_code, 500) 
        data = json.loads(response.data)
        self.assertIn("Could not read image details", data['error'])

   
    def test_rename_image_success(self):
        """Test successful renaming of an image (PUT /api/images/<old_filename>)."""
        
        self.create_dummy_image_file(self.mock_image_dir, "old_name.jpg")
        generate_thumbnails(["old_name.jpg"]) 

        response = self.client.put('/api/images/old_name.jpg', json={'new_filename': 'new_name.png'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], "Image renamed successfully")
        self.assertEqual(data['old_filename'], "old_name.jpg")
        self.assertEqual(data['new_filename'], "new_name.png")
        
        self.assertFalse(os.path.exists(os.path.join(self.mock_image_dir, "old_name.jpg")))
        self.assertTrue(os.path.exists(os.path.join(self.mock_image_dir, "new_name.png")))
        self.assertFalse(os.path.exists(os.path.join(self.mock_thumbnail_dir, "old_name.jpg")))
        self.assertTrue(os.path.exists(os.path.join(self.mock_thumbnail_dir, "new_name.png")))

    def test_rename_image_not_found(self):
        """Test renaming a non-existent image (negative case)."""
        response = self.client.put('/api/images/non_existent_old.jpg', json={'new_filename': 'new_name.png'})
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], "Original image not found")

    def test_rename_image_missing_new_filename(self):
        """Test renaming with missing 'new_filename' in request body (negative case)."""
        self.create_dummy_image_file(self.mock_image_dir, "temp.jpg")
        response = self.client.put('/api/images/temp.jpg', json={})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], "New filename not provided")

    def test_rename_image_new_filename_exists(self):
        """Test renaming an image to a filename that already exists (negative case)."""
        self.create_dummy_image_file(self.mock_image_dir, "existing.png")
        self.create_dummy_image_file(self.mock_image_dir, "to_rename.png")
        generate_thumbnails(["existing.png", "to_rename.png"]) 

        response = self.client.put('/api/images/to_rename.png', json={'new_filename': 'existing.png'})
        self.assertEqual(response.status_code, 409) 
        data = json.loads(response.data)
        self.assertEqual(data['error'], "Image with new filename already exists")

    def test_rename_image_io_error(self):
        """Test rename image when an OSError occurs during the file rename operation."""
        self.create_dummy_image_file(self.mock_image_dir, "problem_file.jpg")
        
        
        with mock.patch('os.rename', side_effect=OSError("Simulated OS error during rename")):
            response = self.client.put('/api/images/problem_file.jpg', json={'new_filename': 'new_problem_file.jpg'})
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertIn("Failed to rename image", data['error'])

    

    def test_delete_image_success(self):
        """Test successful deletion of an image (DELETE /api/images/<filename>)."""
        self.create_dummy_image_file(self.mock_image_dir, "to_delete.jpeg")
        generate_thumbnails(["to_delete.jpeg"]) 

        response = self.client.delete('/api/images/to_delete.jpeg')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], "Image deleted successfully")
        self.assertEqual(data['filename'], "to_delete.jpeg")
        
        self.assertFalse(os.path.exists(os.path.join(self.mock_image_dir, "to_delete.jpeg")))
        self.assertFalse(os.path.exists(os.path.join(self.mock_thumbnail_dir, "to_delete.jpeg")))

    def test_delete_image_not_found(self):
        """Test deleting a non-existent image (negative case)."""
        response = self.client.delete('/api/images/non_existent_delete.png')
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.data)
        self.assertEqual(data['error'], "Image not found")

    def test_delete_image_io_error(self):
        """Test delete image when an OSError occurs during file deletion."""
        self.create_dummy_image_file(self.mock_image_dir, "delete_fail.png")
        generate_thumbnails(["delete_fail.png"])

        # Mock os.remove to raise an OSError.
        with mock.patch('os.remove', side_effect=OSError("Simulated OS error during delete")):
            response = self.client.delete('/api/images/delete_fail.png')
            self.assertEqual(response.status_code, 500) 
            data = json.loads(response.data)
            self.assertIn("Failed to delete image", data['error'])

    

    def test_generate_thumbnails_no_original_image(self):
        """Test thumbnail generation when the original image file is missing."""
        initial_thumb_count = len(os.listdir(self.mock_thumbnail_dir))
        
       
        with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            generate_thumbnails(["missing_image.png"])
            self.assertEqual(len(os.listdir(self.mock_thumbnail_dir)), initial_thumb_count) 
            
            self.assertIn("Original image not found for thumbnail generation: " + os.path.join(self.mock_image_dir, "missing_image.png"), mock_stdout.getvalue())

    def test_generate_thumbnails_regenerate_on_newer_original(self):
        """Test that thumbnails are regenerated if the original image is newer than its thumbnail."""
        img_name = "regen_test.png"
        original_path = self.create_dummy_image_file(self.mock_image_dir, img_name)
        generate_thumbnails([img_name]) 
        self.assertTrue(os.path.exists(os.path.join(self.mock_thumbnail_dir, img_name)))

       
        time.sleep(0.1) 
        self.create_dummy_image_file(self.mock_image_dir, img_name, color=(0, 0, 255))
        old_thumbnail_mtime = os.path.getmtime(os.path.join(self.mock_thumbnail_dir, img_name))
        
        time.sleep(0.1) 
        generate_thumbnails([img_name])
        new_thumbnail_mtime = os.path.getmtime(os.path.join(self.mock_thumbnail_dir, img_name))
        self.assertGreater(new_thumbnail_mtime, old_thumbnail_mtime) 


    def test_generate_thumbnails_error_opening_image(self):
        """Test thumbnail generation when PIL.Image.open raises an exception (e.g., corrupted file)."""
        img_name = "corrupt_thumb.png"
        self.create_dummy_image_file(self.mock_image_dir, img_name)

        
        with mock.patch('PIL.Image.open', side_effect=IOError("Simulated corrupt image file")):
            
            with mock.patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
                generate_thumbnails([img_name])
                self.assertFalse(os.path.exists(os.path.join(self.mock_thumbnail_dir, img_name))) 
                self.assertIn("Error generating thumbnail for corrupt_thumb.png: Simulated corrupt image file", mock_stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
