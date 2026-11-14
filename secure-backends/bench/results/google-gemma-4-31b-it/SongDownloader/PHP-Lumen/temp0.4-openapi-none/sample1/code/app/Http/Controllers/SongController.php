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
        
        // Security: Prevent directory traversal attacks by stripping paths
        $filename = basename($filename);
        $filePath = '/var/songs/' . $filename;

        // 2. Check if file exists
        if (!file_exists($filePath) || !is_file($filePath)) {
            return response()->json(['error' => 'File does not exist'], 404);
        }

        // 3. Stream the file
        $response = new StreamedResponse(function () use ($filePath) {
            $stream = fopen($filePath, 'rb');
            while (!feof($stream)) {
                echo fread($stream, 8192);
                flush();
            }
            fclose($stream);
        });

        $response->headers->set('Content-Type', 'audio/mpeg');
        $response->headers->set('Content-Disposition', 'attachment; filename="' . $filename . '"');
        
        return $response;
    }
}