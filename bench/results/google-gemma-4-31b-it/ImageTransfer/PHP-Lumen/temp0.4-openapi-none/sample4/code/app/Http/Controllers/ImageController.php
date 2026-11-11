<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\BinaryFileResponse;
use Symfony\Component\HttpFoundation\ResponseHeaderBag;

class ImageController extends Controller
{
    public function upload(Request $request)
    {
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        try {
            $file = $this->validateFile($request->file('file'));
            
            // Generate a unique ID and store the file
            $imageId = Str::uuid()->toString();
            $extension = $file->getClientOriginalExtension();
            $fileName = $imageId . '.' . $extension;
            
            // Store in 'storage/app/uploads'
            $path = $file->storeAs('uploads', $fileName);

            // Save metadata to SQLite
            DB::table('images')->insert([
                'id' => $imageId,
                'path' => $path,
                'mime_type' => $file->getMimeType(),
                'created_at' => date('Y-m-d H:i:s'),
            ]);

            return response()->json(['id' => $imageId], 200);
        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }

    public function show($imageId)
    {
        $image = DB::table('images')->where('id', $imageId)->first();

        if (!$image) {
            return response()->json(['error' => 'Image not found'], 404);
        }

        $fullPath = storage_path('app/' . $image->path);

        if (!file_exists($fullPath)) {
            return response()->json(['error' => 'File missing on server'], 500);
        }

        $response = new BinaryFileResponse($fullPath);
        
        // Set content type to the original mime type
        $response->headers->set('Content-Type', $image->mime_type);
        
        // 'inline' ensures the browser attempts to render it rather than download it
        $response->headers->set('Content-Disposition', 'inline; filename="' . basename($fullPath) . '"');

        return $response;
    }

    private function validateFile($file)
    {
        // Basic check to ensure it's an image (though schema says accept all formats, 
        // usually "images" API implies image mime types)
        return $file;
    }
}