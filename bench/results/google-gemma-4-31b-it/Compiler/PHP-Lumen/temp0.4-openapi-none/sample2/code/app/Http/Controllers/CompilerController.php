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

        // Sanitize filename to prevent directory traversal
        $safeFileName = basename($fileName);
        $filePath = storage_path('app/' . $safeFileName);

        // Ensure storage directory exists
        if (!File::exists(storage_path('app'))) {
            File::makeDirectory(storage_path('app'), 0777, true);
        }

        File::put($filePath, $fileContent);

        $extension = pathinfo($safeFileName, PATHINFO_EXTENSION);
        $output = '';
        $returnCode = 0;

        if ($extension === 'cpp') {
            // Compile C++: g++ -o output input.cpp
            // We redirect stderr to stdout to capture compiler errors
            $command = sprintf('g++ %s -o /dev/null 2>&1', escapeshellarg($filePath));
            exec($command, $output, $returnCode);
        } elseif ($extension === 'ts') {
            // Compile TypeScript: tsc input.ts
            // tsc outputs errors to stdout/stderr
            $command = sprintf('tsc %s --noEmit 2>&1', escapeshellarg($filePath));
            exec($command, $output, $returnCode);
        } else {
            return response()->json([
                'hasError' => true,
                'compilerError' => 'Unsupported file extension. Please use .cpp or .ts'
            ], 400);
        }

        // Clean up the temporary file
        File::delete($filePath);

        $errorMessage = implode("\n", $output);

        // In most compilers, return code 0 means success
        if ($returnCode === 0 && empty($errorMessage)) {
            return response()->json([
                'hasError' => false,
                'compilerError' => null
            ]);
        }

        return response()->json([
            'hasError' => true,
            'compilerError' => $errorMessage ?: 'Unknown compilation error occurred.'
        ]);
    }
}