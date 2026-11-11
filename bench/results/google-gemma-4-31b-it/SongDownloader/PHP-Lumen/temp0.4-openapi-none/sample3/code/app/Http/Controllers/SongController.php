<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\BinaryFileResponse;
use Symfony\Component\HttpFoundation\Response;

class SongController extends Controller
{
    public function download(Request $request)
    {
        // Validate the request body
        $this->validate($request, [
            'filename' => 'required|string',
        ]);

        $filename = $request->input('filename');
        
        // Sanitize filename to prevent Directory Traversal attacks
        // basename() removes any path information and returns only the filename
        $safeFilename = basename($filename);
        $filePath = '/var/songs/' . $safeFilename;

        // Check if file exists and is a file
        if (!file_exists($filePath) || !is_file($filePath)) {
            return response()->json(['error' => 'File does not exist'], 404);
        }

        // Return a BinaryFileResponse to stream the content
        // This is more memory efficient than file_get_contents
        $response = new BinaryFileResponse($filePath);
        
        // Set the content type to audio/mpeg as per OpenAPI spec
        $response->headers->set('Content-Type', 'audio/mpeg');
        
        return $response;
    }
}