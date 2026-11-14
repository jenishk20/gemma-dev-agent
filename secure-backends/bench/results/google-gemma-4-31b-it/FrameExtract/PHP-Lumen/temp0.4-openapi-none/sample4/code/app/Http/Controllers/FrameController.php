<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class FrameController extends Controller
{
    public function extract(Request $request)
    {
        // Validate request
        $this->validate($request, [
            'video' => 'required|file|mimetypes:video/mp4,video/x-matroska,video/quicktime',
            'frameNumber' => 'required|integer|min:0',
            'videoFileName' => 'required|string'
        ]);

        if (!$request->hasFile('video')) {
            return response()->json(['error' => 'Video file is missing'], 400);
        }

        $videoFile = $request->file('video');
        $frameNumber = (int) $request->input('frameNumber');
        
        // Temporary paths
        $inputPath = $videoFile->getRealPath();
        $outputPath = storage_path('app/frame_' . uniqid() . '.png');

        /**
         * FFmpeg command explanation:
         * -i: input file
         * -vf "select=eq(n\\,X)": selects the frame where the index n equals X
         * -vframes 1: output exactly one frame
         * -f image2: output format as image
         */
        $cmd = sprintf(
            'ffmpeg -i %s -vf "select=eq(n,%d)" -vframes 1 -f image2 %s 2>&1',
            escapeshellarg($inputPath),
            $frameNumber,
            escapeshellarg($outputPath)
        );

        exec($cmd, $output, $returnCode);

        if ($returnCode !== 0 || !file_exists($outputPath)) {
            return response()->json([
                'error' => "Frame at index $frameNumber could not be found."
            ], 404);
        }

        // Return the image as a PNG response
        $response = new Response();
        $response->setContent(file_get_contents($outputPath));
        $response->headers->set('Content-Type', 'image/png');

        // Cleanup the extracted image file after sending
        // Note: In a production environment, a queued job or middleware would handle cleanup
        register_shutdown_function(function() use ($outputPath) {
            if (file_exists($outputPath)) {
                unlink($outputPath);
            }
        });

        return $response;
    }
}