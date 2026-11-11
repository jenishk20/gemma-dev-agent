<?php

namespace App\Http\Controllers;

use App\Models\Image;
use Illuminate\Http\Request;
use Illuminate\Support\Str;
use Illuminate\Support\Facades\Storage;

class ImageController extends Controller
{
    public function upload(Request $request)
    {
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        try {
            $file = $request->file('file');
            
            // Generate a unique ID for the image
            $id = Str::uuid()->toString();
            $extension = $file->getClientOriginalExtension();
            $filename = $id . '.' . $extension;
            $mimeType = $file->getMimeType();

            // Store the file in the 'uploads' directory
            $path = $file->storeAs('uploads', $filename);

            // Save metadata to SQLite
            Image::create([
                'id' => $id,
                'filename' => $filename,
                'mime_type' => $mimeType
            ]);

            return response()->json(['id' => $id], 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }

    public function show($imageId)
    {
        try {
            $image = Image::find($imageId);

            if (!$image) {
                return response()->json(['error' => 'Image not found'], 404);
            }

            $filePath = storage_path('app/' . 'uploads/' . $image->filename);

            if (!file_exists($filePath)) {
                return response()->json(['error' => 'Image file missing from storage'], 404);
            }

            // Return the file with the original mime type
            // 'inline' disposition ensures it is viewed in browser, not downloaded
            return response()->file($filePath, [
                'Content-Type' => $image->mime_type,
                'Content-Disposition' => 'inline; filename="' . $image->filename . '"'
            ]);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }
}