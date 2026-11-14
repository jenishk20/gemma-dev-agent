<?php

namespace App\Http\Controllers;

use App\Models\Image;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class ImageController extends Controller
{
    public function upload(Request $request)
    {
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        try {
            $file = $request->file('file');
            
            // Generate a unique ID for the file
            $id = Str::uuid()->toString();
            $extension = $file->getClientOriginalExtension();
            $filename = $id . '.' . $extension;
            
            // Store the file in storage/app/uploads
            $path = $file->storeAs('uploads', $filename);

            // Save metadata to SQLite
            $image = Image::create([
                'id' => $id,
                'original_name' => $file->getClientOriginalName(),
                'mime_type' => $file->getMimeType(),
                'path' => $path,
            ]);

            return response()->json(['id' => $image->id], 200);
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

            if (!Storage::exists($image->path)) {
                return response()->json(['error' => 'File missing from storage'], 404);
            }

            $fileContents = Storage::get($image->path);
            
            // Return the file with the original mime type. 
            // By not setting Content-Disposition to 'attachment', the browser will attempt to render it.
            return response($fileContents, 200, [
                'Content-Type' => $image->mime_type,
                'Content-Length' => Storage::size($image->path),
            ]);
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }
}