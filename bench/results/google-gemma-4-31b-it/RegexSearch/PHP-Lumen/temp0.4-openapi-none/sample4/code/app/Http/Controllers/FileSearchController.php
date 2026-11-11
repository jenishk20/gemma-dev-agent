<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use RecursiveIteratorIterator;
use RecursiveDirectoryIterator;

class FileSearchController extends Controller
{
    public function search(Request $request)
    {
        $regex = $request->query('regex');
        $directoryParam = $request->query('directory', '');
        $recursive = filter_var($request->query('recursive', false), FILTER_VALIDATE_BOOLEAN);

        if (!$regex) {
            return response()->json(['error' => 'The regex parameter is required.'], 400);
        }

        // Validate regex syntax
        if (@preg_match('~' . $regex . '~', '') === false) {
            return response()->json(['error' => 'Invalid regex pattern provided.'], 400);
        }

        $rootPath = base_path('files');
        
        // Construct the target search path
        $searchPath = rtrim($rootPath . DIRECTORY_SEPARATOR . trim($directoryParam, '/'), DIRECTORY_SEPARATOR);

        if (!File::exists($searchPath) || !File::isDirectory($searchPath)) {
            return response()->json(['error' => 'Specified directory does not exist or is inaccessible.'], 400);
        }

        try {
            $matchingFiles = [];
            
            if ($recursive) {
                $iterator = new RecursiveIteratorIterator(
                    new RecursiveDirectoryIterator($searchPath, RecursiveDirectoryIterator::SKIP_DOTS)
                );
            } else {
                $iterator = new RecursiveDirectoryIterator($searchPath, RecursiveDirectoryIterator::SKIP_DOTS);
            }

            foreach ($iterator as $file) {
                if ($file->isFile()) {
                    $filePath = $file->getPathname();
                    $content = file_get_contents($filePath);
                    
                    if (preg_match('~' . $regex . '~', $content)) {
                        // Calculate path relative to the requested directory
                        $relative = str_replace($searchPath . DIRECTORY_SEPARATOR, '', $filePath);
                        $matchingFiles[] = $relative;
                    }
                }
            }

            return response()->json(['files' => $matchingFiles], 200);

        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal server error: ' . $e->getMessage()], 500);
        }
    }
}