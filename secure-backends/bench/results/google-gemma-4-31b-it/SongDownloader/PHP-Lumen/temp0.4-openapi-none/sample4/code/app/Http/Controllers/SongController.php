<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;
use Symfony\Component\HttpFoundation\ResponseHeaderBag;

class SongController extends Controller
{
    /**
     * Retrieve the chosen song from the server
     * 
     * @param Request $request
     * @return \Illuminate\Http\Response
     */
    public function download(Request $request)
    {
        // Validate the request body
        $this->validate($request, [
            'filename' => 'required|string'
        ]);

        $filename = $request->input('filename');
        
        // Security: Prevent directory traversal by extracting only the base name
        $safeFilename = basename($filename);
        $filePath = '/var/songs/' . $safeFilename;

        // Check if file exists and is actually a file
        if (!file_exists($filePath) || !is_file($filePath)) {
            return response()->json(['error' => 'File does not exist'], 404);
        }

        // Use BinaryFileResponse for efficient streaming of large files
        $response = new BinaryFileResponse($filePath);
        
        // Set the content type to audio/mpeg as per OpenAPI spec
        $response->headers->set('Content-Type', 'audio/mpeg');
        
        // Set headers to ensure the browser treats it as a stream/attachment
        $response->headers->set(ResponseHeaderBag::DISPOSITION, 'attachment; filename="' . $safeFilename . '"');

        return $response;
    }
}