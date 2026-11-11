<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Process;

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

        // Use system temp dir to avoid permission issues
        $tempDir = sys_get_temp_dir();
        $filePath = $tempDir . DIRECTORY_SEPARATOR . $fileName;

        // Write the content to a file
        file_put_contents($filePath, $fileContent);

        $extension = pathinfo($fileName, PATHINFO_EXTENSION);
        $command = '';

        if ($extension === 'cpp') {
            // Compile C++: -fexec-charset=UTF-8 ensures consistent output
            // We use -o /dev/null because we only care about compilation success/failure
            $command = sprintf('g++ %s -o %s/a.out 2>&1', escapeshellarg($filePath), escapeshellarg($tempDir));
        } elseif ($extension === 'ts') {
            // Compile TypeScript: tsc returns errors to stdout/stderr
            // --noEmit prevents creating .js files
            $command = sprintf('tsc %s --noEmit 2>&1', escapeshellarg($filePath));
        } else {
            return response()->json([
                'hasError' => true,
                'compilerError' => 'Unsupported file extension. Please use .cpp or .ts'
            ], 400);
        }

        // Execute the command
        $output = [];
        $returnVar = 0;
        exec($command, $output, $returnVar);

        $errorOutput = implode("\n", $output);
        $hasError = ($returnVar !== 0);

        // Cleanup the temporary file
        if (file_exists($filePath)) {
            unlink($filePath);
        }

        return response()->json([
            'hasError' => $hasError,
            'compilerError' => $hasError ? $errorOutput : null,
        ]);
    }
}