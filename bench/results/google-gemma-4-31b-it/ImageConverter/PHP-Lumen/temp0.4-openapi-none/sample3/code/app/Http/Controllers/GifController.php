<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Validator;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class GifController extends Controller
{
    public function create(Request $request)
    {
        // 1. Validation
        $validator = Validator::make($request->all(), [
            'images' => 'required|array',
            'images.*' => 'required|file|image',
            'targetSize' => 'required|string|regex:/^\d+x\d+$/',
            'delay' => 'integer',
            'appendReverted' => 'boolean',
        ]);

        if ($validator->fails()) {
            return response()->json(['error' => $validator->errors()->first()], 400);
        }

        try {
            $images = $request->file('images');
            $targetSize = $request->input('targetSize');
            $delay = $request->input('delay', 10);
            $appendReverted = $request->boolean('appendReverted');

            // Create a temporary directory for processing
            $tmpDir = sys_get_temp_dir() . '/gif_creator_' . uniqid();
            mkdir($tmpDir);

            $savedFiles = [];
            foreach ($images as $index => $file) {
                $path = $tmpDir . "/frame_{$index}.png";
                $file->move($tmpDir, "frame_{$index}.png");
                $savedFiles[] = $path;
            }

            // Handle "appendReverted" (Ping-pong effect)
            if ($appendReverted && count($savedFiles) > 1) {
                $reversed = array_reverse(array_slice($savedFiles, 0, -1));
                // Avoid duplicating the last frame if it's the same as the first of the reverse
                $reversed = array_slice($reversed, 1); 
                $savedFiles = array_merge($savedFiles, $reversed);
            }

            $outputFile = $tmpDir . '/result.gif';
            
            // ImageMagick Command Construction
            // -delay is in ticks (1/100th of a second), so ms / 10
            $delayTicks = (int)($delay / 10);
            
            $cmd = sprintf(
                'convert -delay %d -loop 0 -resize %s %s %s',
                $delayTicks,
                escapeshellarg($targetSize),
                implode(' ', array_map('escapeshellarg', $savedFiles)),
                escapeshellarg($outputFile)
            );

            exec($cmd, $output, $returnVar);

            if ($returnVar !== 0) {
                throw new \Exception("ImageMagick conversion failed.");
            }

            // Return the GIF file as a response
            return response()->file($outputFile, null, ['Content-Type' => 'image/gif']);

        } catch (\Exception $e) {
            return response()->json(['error' => $e->getMessage()], 500);
        }
    }
}