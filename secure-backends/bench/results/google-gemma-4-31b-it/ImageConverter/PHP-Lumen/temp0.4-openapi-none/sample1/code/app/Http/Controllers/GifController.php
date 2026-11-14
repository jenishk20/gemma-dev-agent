<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class GifController extends Controller
{
    public function create(Request $request)
    {
        // 1. Validation
        if (!$request->hasFile('images') || !$request->has('targetSize')) {
            return response()->json(['error' => 'Missing required fields: images and targetSize'], 400);
        }

        $files = $request->file('images');
        if (!is_array($files)) {
            // Handle case where only one file is uploaded but it's not passed as an array
            $files = [$files];
        }

        $targetSize = $request->input('targetSize');
        $delay = (int) $request->input('delay', 10);
        $appendReverted = filter_var($request->input('appendReverted'), FILTER_VALIDATE_BOOLEAN);

        if (empty($files)) {
            return response()->json(['error' => 'No images provided'], 400);
        }

        try {
            // 2. Setup temporary directory
            $tempDir = storage_path('app/gif_temp_' . uniqid());
            if (!File::exists($tempDir)) {
                File::makeDirectory($tempDir, 0777, true);
            }

            $imagePaths = [];
            foreach ($files as $index => $file) {
                $extension = $file->getClientOriginalExtension();
                $filename = "frame_{$index}.{$extension}";
                $path = $tempDir . DIRECTORY_SEPARATOR . $filename;
                $file->move($tempDir, $filename);
                $imagePaths[] = $path;
            }

            // 3. Handle Reverted sequence
            if ($appendReverted) {
                $reverted = array_reverse($imagePaths);
                // To avoid duplicating files on disk, we just use the paths in the command
                $finalSequence = array_merge($imagePaths, $reverted);
            } else {
                $finalSequence = $imagePaths;
            }

            // 4. Construct ImageMagick Command
            // -delay is in ticks (1/100th of a second), so ms / 10
            $delayTicks = $delay / 10;
            $outputFile = $tempDir . DIRECTORY_SEPARATOR . 'result.gif';
            
            // Escape paths for shell
            $escapedPaths = array_map(fn($p) => escapeshellarg($p), $finalSequence);
            $pathsString = implode(' ', $escapedPaths);
            
            $cmd = sprintf(
                "convert -delay %f -loop 0 -resize %s %s %s",
                $delayTicks,
                escapeshellarg($targetSize),
                $pathsString,
                escapeshellarg($outputFile)
            );

            exec($cmd, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("ImageMagick conversion failed");
            }

            // 5. Return the file and cleanup
            $content = file_get_contents($outputFile);
            
            // Cleanup temp files
            File::deleteDirectory($tempDir);

            return response($content, 200)
                ->header('Content-Type', 'image/gif');

        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal Server Error: ' . $e->getMessage()], 500);
        }
    }
}