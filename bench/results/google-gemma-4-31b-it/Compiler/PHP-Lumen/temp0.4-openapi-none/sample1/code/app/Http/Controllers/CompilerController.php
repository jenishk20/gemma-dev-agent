<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class CompilerController extends Controller
{
    public function compile(Request $request)
    {
        $this->validate($request, [
            'fileName' => 'required|string',
            'fileContent' => 'required|string',
        ]);

        $fileName = $request->input('fileName');
        $fileContent = $request->input('fileContent');
        
        // Create a unique temporary directory for this request to avoid collisions
        $tmpDir = storage_path('app/compilation_' . uniqid());
        if (!File::exists($tmpDir)) {
            File::makeDirectory($tmpDir, 0777, true);
        }

        $filePath = $tmpDir . '/' . $fileName;
        File::put($filePath, $fileContent);

        $extension = pathinfo($fileName, PATHINFO_EXTENSION);
        $output = "";
        $returnVar = 0;

        if ($extension === 'cpp') {
            // Compile C++: g++ -o output input.cpp
            // We capture stderr (2>&1)
            $command = sprintf('g++ %s -o %s 2>&1', escapeshellarg($filePath), escapeshellarg($tmpDir . '/out'));
            exec($command, $output, $returnVar);
        } elseif ($extension === 'ts') {
            // Compile TypeScript: tsc input.ts
            // tsc outputs errors to stdout/stderr
            $command = sprintf('tsc %s --noEmit 2>&1', escapeshellarg($filePath));
            exec($command, $output, $returnVar);
        } else {
            return response()->json(['error' => 'Unsupported file extension'], 400);
        }

        $hasError = $returnVar !== 0;
        $compilerError = $hasError ? implode("\n", $output) : null;

        // Cleanup temporary files
        File::deleteDirectory($tmpDir);

        return response()->json([
            'hasError' => $hasError,
            'compilerError' => $compilerError,
        ]);
    }
}