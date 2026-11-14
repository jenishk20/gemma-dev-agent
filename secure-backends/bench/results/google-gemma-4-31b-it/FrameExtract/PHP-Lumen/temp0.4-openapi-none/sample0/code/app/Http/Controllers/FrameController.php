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
            'frameNumber' => 'required|integer|min:0',
        ]);

        $videoFile = $request->file('video');
        $frameNumber = (int) $request->input('frameNumber');
        
        // Setup temporary paths
        $tempDir = storage_path('tmp');
        if (!File::exists($tempDir)) {
            File::makeDirectory($tempDir, 0777, true);
        }

        $inputPath = $tempDir . '/' . uniqid() . '_' . $videoFile->getClientOriginalName();
        $outputPath = $tempDir . '/' . uniqid() . '.png';

        // Move uploaded file to temp storage
        $videoFile->move($tempDir, basename($inputPath));

        /**
         * FFmpeg command explanation:
         * -i: input file
         * -vf "select=eq(n\,FRAME_INDEX)": filter to select the specific frame index
         * -vframes 1: output exactly one frame
         * -q:v 2: high quality
         */
        $cmd = sprintf(
            'ffmpeg -i %s -vf "select=eq(n\,%d)" -vframes 1 -q:v 2 %s 2>&1',
            escapeshellarg($inputPath),
            $frameNumber,
            escapeshellarg($outputPath)
        );

        exec($cmd, $output, $returnVar);

        // Cleanup input video immediately
        File::delete($inputPath);

        if ($returnVar !== 0 || !File::exists($outputPath)) {
            return response()->json([
                'error' => "Frame at index $frameNumber could not be found."
            ], 404);
        }

        // Read the image content
        $imageContent = File::get($outputPath);
        
        // Cleanup output image
        File::delete($outputPath);

        return response($imageContent)
            ->header('Content-Type', 'image/png');
    }
}