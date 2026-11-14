<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use Symfony\Component\HttpFoundation\BinaryFileResponse;
use Symfony\Component\HttpFoundation\Response;

class FrameController extends Controller
{
    public function extract(Request $request)
    {
        // Validate inputs
        $this->validate($request, [
            'video' => 'required|file|mimetypes:video/mp4,video/quicktime,video/x-msvideo',
            'frameNumber' => 'required|integer|min:0',
        ]);

        if (!$request->hasFile('video')) {
            return response()->json(['error' => 'Video file is missing'], 400);
        }

        $videoFile = $request->file('video');
        $frameNumber = (int) $request->input('frameNumber');
        
        // Create temporary paths
        $tempDir = storage_path('app/temp');
        if (!File::exists($tempDir)) {
            File::makeDirectory($tempDir, 0777, true);
        }

        $inputPath = $tempDir . '/' . uniqid() . '_' . $videoFile->getClientOriginalName();
        $outputPath = $tempDir . '/' . uniqid() . '.png';

        // Move uploaded file to temp storage
        $videoFile->move($tempDir, basename($inputPath));

        /**
         * ffmpeg command explanation:
         * -i: input file
         * -vf "select='eq(n\\,FRAME_INDEX)'": selects the specific frame index
         * -vframes 1: output exactly one frame
         * -f image2: force image format
         */
        $cmd = sprintf(
            'ffmpeg -i %s -vf "select=\'eq(n\\,%d)\'" -vframes 1 -f image2 %s 2>&1',
            escapeshellarg($inputPath),
            $frameNumber,
            escapeshellarg($outputPath)
        );

        exec($cmd, $output, $returnCode);

        // Clean up input video immediately
        File::delete($inputPath);

        // Check if output file was actually created and is not empty
        if ($returnCode !== 0 || !File::exists($outputPath) || File::size($outputPath) === 0) {
            return response()->json([
                'error' => "Frame at index $frameNumber could not be found."
            ], 404);
        }

        // Return the image as a binary response
        return new BinaryFileResponse($outputPath, 200, [
            'Content-Type' => 'image/png',
            'Content-Disposition' => 'inline; filename="frame.png"'
        ]);
        
        // Note: In a production environment, you would use a queued job 
        // or a middleware to clean up the $outputPath after the response is sent.
    }
}