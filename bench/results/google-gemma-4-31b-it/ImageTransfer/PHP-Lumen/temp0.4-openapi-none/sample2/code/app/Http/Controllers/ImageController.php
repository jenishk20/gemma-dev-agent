<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

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
            $id = Str::uuid()->toString();
            $extension = $file->getClientOriginalExtension();
            $filename = $id . '.' . $extension;

            // Store the file in the 'uploads' directory
            $path = $file->storeAs('uploads', $filename);

            // Store metadata in SQLite
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

            $fullPath = storage_path('app/' . $image->path);

            if (!file_exists($fullPath)) {
                return response()->json(['error' => 'File not found on disk'], 404);
            }

            // BinaryFileResponse handles the streaming of the file.
            // We set the Content-Type and ensure Content-Disposition is 'inline' 
            // so the browser displays it instead of downloading it.
            return new BinaryFileResponse(
                $fullPath,
                100,
                $image->mime_type,
                true,
                'inline'
            );
        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error'], 500);
        }
    }
}