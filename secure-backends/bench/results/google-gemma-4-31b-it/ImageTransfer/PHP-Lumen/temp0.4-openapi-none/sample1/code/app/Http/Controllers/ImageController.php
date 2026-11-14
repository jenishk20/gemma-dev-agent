<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use App\Models\Image;
use Illuminate\Support\Facades\DB;

class ImageController extends Controller
{
    public function upload(Request $request)
    {
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        try {
            $file = $request->file('file');
            
            // Generate a unique ID and filename
            $id = (string) Str::uuid();
            $extension = $file->getClientOriginalExtension();
            $filename = $id . '.' . $extension;
            
            // Store file in storage/app/uploads
            $path = $file->storeAs('uploads', $filename);

            // Save metadata to SQLite
            DB::table('images')->insert([
                'id' => $id,
                'path' => $path,
                'mime_type' => $file->getMimeType(),
                'created_at' => date('Y-m-d H:i:s'),
                'updated_at' => date('Y-m-d H:i:s'),
            ]);

            return response()->json(['id' => $id], 200);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error: ' . $e->getMessage()], 500);
        }
    }

    public function show($imageId)
    {
        try {
            $image = DB::table('images')->where('id', $imageId)->first();

            if (!$image) {
                return response()->json(['error' => 'Image not found'], 404);
            }

            $path = storage_path('app/' . $image->path);

            if (!file_exists($path)) {
                return response()->json(['error' => 'File not found on disk'], 404);
            }

            // Return the file with the original mime type. 
            // Lumen/Laravel response()->file() sets Content-Type and avoids Content-Disposition: attachment
            return response()->file($path, [
                'Content-Type' => $image->mime_type,
                'Content-Disposition' => 'inline'
            ]);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }
}