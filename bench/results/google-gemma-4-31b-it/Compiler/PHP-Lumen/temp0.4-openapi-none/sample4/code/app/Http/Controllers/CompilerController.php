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
        $tempDir = storage_path('app/compilation_' . uniqid());
        if (!File::exists($tempDir)) {
            File::makeDirectory($tempDir, 0777, true);
        }

        $filePath = $tempDir . '/' . $fileName;
        File::put($filePath, $fileContent);

        $extension = pathinfo($fileName, PATHINFO_EXTENSION);
        $command = '';

        if ($extension === 'cpp') {
            // Compile C++: g++ -c (compile only) to check for errors without needing a main() return 0 strictly
            // We use -fsyntax-only if available or just g++ -c
            $command = sprintf('g++ -c %s 2>&1', escapeshellarg($filePath));
        } elseif ($extension === 'ts') {
            // Compile TypeScript: tsc (using the global installation)
            // --noEmit prevents generating .js files
            $command = sprintf('tsc %s --noEmit 2>&1', escapeshellarg($filePath));
        } else {
            return response()->json(['error' => 'Unsupported file extension'], 400);
        }

        $output = [];
        $returnVar = 0;
        exec($command, $output, $returnVar);

        $errorOutput = implode("\n", $output);
        $hasError = ($returnVar !== 0);

        // Cleanup temporary files
        File::deleteDirectory($tempDir);

        return response()->json([
            'hasError' => $hasError,
            'compilerError' => $hasError ? $errorOutput : null,
        ]);
    }
}