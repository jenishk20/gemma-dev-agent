<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class FrameController extends Controller
{
    public function extract(Request $request)
    {
        // Validate inputs
        $this->validate($request, [
            'video' => 'required|file',
            'frameNumber' => 'required|integer',
            'videoFileName' => 'required|string',
        ]);

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
         * -vf "select=eq(n\,FRAME_INDEX)": selects the specific frame index
         * -vframes 1: output exactly one frame
         * -f image2: force image format
         */
        $cmd = sprintf(
            'ffmpeg -i %s -vf "select=eq(n\,%d)" -vframes 1 -f image2 %s 2>&1',
            escapeshellarg($inputPath),
            $frameNumber,
            escapeshellarg($outputPath)
        );

        $output = shell_exec($cmd);

        // Check if file was actually created
        if (!File::exists($outputPath)) {
            // Cleanup input file
            File::delete($inputPath);
            return response()->json([
                'error' => "Frame at index $frameNumber could not be found."
            ], 404);
        }

        // Read image content
        $imageContent = File::get($outputPath);

        // Cleanup temporary files
        File::delete($inputPath);
        File::delete($outputPath);

        return response($imageContent, 200, [
            'Content-Type' => 'image/png',
            'Content-Disposition' => 'inline; filename="frame.png"'
        ]);
    }
}