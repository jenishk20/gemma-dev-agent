<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\StreamedResponse;

class SongController extends Controller
{
    public function download(Request $request)
    {
        // 1. Validate Input
        $this->validate($request, [
            'filename' => 'required|string'
        ]);

        $filename = $request->input('filename');
        
        // Security: Prevent directory traversal attacks
        // basename() removes any path information and returns only the filename
        $safeFilename = basename($filename);
        $filePath = '/var/songs/' . $safeFilename;

        // 2. Check if file exists
        if (!file_exists($filePath)) {
            return response()->json(['error' => 'File does not exist'], 404);
        }

        // 3. Stream the file
        $response = new StreamedResponse(function () use ($filePath) {
            $stream = fopen($filePath, 'rb');
            fpassthru($stream);
            fclose($stream);
        });

        $response->headers->set('Content-Type', 'audio/mpeg');
        $response->headers->set('Content-Length', filesize($filePath));
        $response->headers->set('Content-Disposition', 'attachment; filename="' . $safeFilename . '"');

        return $response;
    }
}