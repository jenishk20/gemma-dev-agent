<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\StreamedResponse;

class SongController extends Controller
{
    /**
     * Retrieve the chosen song from the server.
     * 
     * @param Request $request
     * @return \Illuminate\Http\Response|\Symfony\Component\HttpFoundation\StreamedResponse
     */
    public function download(Request $request)
    {
        // Validate input
        $this->validate($request, [
            'filename' => 'required|string'
        ]);

        $filename = $request->input('filename');
        
        // Sanitize filename to prevent Directory Traversal attacks
        // basename() removes any path components provided by the user
        $safeFilename = basename($filename);
        $filePath = '/var/songs/' . $safeFilename;

        if (!file_exists($filePath) || is_dir($filePath)) {
            return response()->json(['error' => 'File does not exist'], 404);
        }

        // Return a streamed response for the audio file
        return new StreamedResponse(function () use ($filePath) {
            $stream = fopen($filePath, 'rb');
            fpassthru($stream);
            fclose($stream);
        }, 200, [
            'Content-Type' => 'audio/mpeg',
            'Content-Length' => filesize($filePath),
            'Content-Disposition' => 'attachment; filename="' . basename($filePath) . '"',
        ]);
    }
}