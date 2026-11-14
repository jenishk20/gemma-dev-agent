<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class FrameController extends Controller
{
    public function extract(Request $request)
    {
        // Validate inputs
        if (!$request->hasFile('video') || !$request->has('frameNumber')) {
            return response()->json(['error' => 'Missing video file or frameNumber'], 400);
        }

        $frameNumber = (int) $request->input('frameNumber');
        $videoFile = $request->file('video');
        
        // Store video temporarily
        $tempVideoPath = storage_path('app/temp_video_' . uniqid() . '.mp4');
        $videoFile->move(storage_path('app'), basename($tempVideoPath));

        // Define output path for the frame
        $tempImagePath = storage_path('app/frame_' . uniqid() . '.png');

        /**
         * ffmpeg command explanation:
         * -i: input file
         * -vf "select=eq(n,X)": select the frame where index n equals X
         * -vframes 1: output exactly one frame
         * -f image2: force image format
         */
        $command = sprintf(
            'ffmpeg -i %s -vf "select=eq(n,%d)" -vframes 1 -f image2 %s 2>&1',
            escapeshellarg($tempVideoPath),
            $frameNumber,
            escapeshellarg($tempImagePath)
        );

        exec($command, $output, $returnVar);

        // Clean up video immediately
        if (File::exists($tempVideoPath)) {
            File::delete($tempVideoPath);
        }

        // Check if the image was actually created (ffmpeg returns 0 even if frame is out of range sometimes, 
        // but the file won't exist or will be empty if the select filter found nothing)
        if ($returnVar !== 0 || !File::exists($tempImagePath) || File::size($tempImagePath) === 0) {
            if (File::exists($tempImagePath)) {
                File::delete($tempImagePath);
            }
            return response()->json([
                'error' => "Frame at index $frameNumber could not be found."
            ], 404);
        }

        // Return the image and delete it after sending
        $imageContent = File::get($tempImagePath);
        File::delete($tempImagePath);

        return response($imageContent, 200)
            ->header('Content-Type', 'image/png');
    }
}