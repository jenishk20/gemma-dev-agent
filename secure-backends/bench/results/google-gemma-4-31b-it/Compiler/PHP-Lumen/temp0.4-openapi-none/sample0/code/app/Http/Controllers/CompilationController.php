<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;

class CompilationController extends Controller
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
        $tempDir = storage_path('app/compilations/' . uniqid());
        if (!File::exists($tempDir)) {
            File::makeDirectory($tempDir, 0777, true);
        }

        $filePath = $tempDir . '/' . $fileName;
        File::put($filePath, $fileContent);

        $extension = pathinfo($fileName, PATHINFO_EXTENSION);
        $output = null;
        $hasError = false;

        if ($extension === 'cpp') {
            // Compile C++: g++ file.cpp -o out
            // We capture stderr (2>&1) because compilers send errors there
            $command = sprintf('g++ %s -o %s 2>&1', escapeshellarg($filePath), escapeshellarg($tempDir . '/out'));
            $output = shell_exec($command);
            
            // g++ returns non-zero exit code on failure. 
            // Since shell_exec doesn't give exit code, we check if output is non-empty 
            // or if the output file was not created.
            if (!empty($output) || !File::exists($tempDir . '/out')) {
                $hasError = true;
            }
        } elseif ($extension === 'ts') {
            // Compile TypeScript: tsc file.ts --noEmit
            // --noEmit is used because we only care about the compiler feedback, not the JS output
            $command = sprintf('tsc %s --noEmit 2>&1', escapeshellarg($filePath));
            $output = shell_exec($command);
            
            if (!empty($output)) {
                $hasError = true;
            }
        } else {
            return response()->json([
                'hasError' => true,
                'compilerError' => 'Unsupported file extension. Please use .cpp or .ts'
            ], 400);
        }

        // Cleanup temporary files
        File::deleteDirectory($tempDir);

        return response()->json([
            'hasError' => $hasError,
            'compilerError' => $hasError ? trim($output) : null,
        ]);
    }
}