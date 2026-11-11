<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;
use Exception;

class FileSearchController extends Controller
{
    private $rootPath = './files';

    public function search(Request $request): JsonResponse
    {
        $regex = $request->query('regex');
        $directory = $request->query('directory', '');
        $recursive = filter_var($request->query('recursive', false), FILTER_VALIDATE_BOOLEAN);

        if (!$regex) {
            return response()->json(['error' => 'The regex parameter is required.'], 400);
        }

        // Validate regex syntax
        if (@preg_match('~' . $regex . '~', '') === false) {
            return response()->json(['error' => 'Invalid regex pattern provided.'], 400);
        }

        // Resolve and validate the search directory
        $searchPath = realpath($this->rootPath . DIRECTORY_SEPARATOR . $directory);
        
        // Ensure the path exists and is actually within the root ./files directory to prevent directory traversal attacks
        if (!$searchPath || !is_dir($searchPath) || strpos($searchPath, realpath($this->rootPath)) !== 0) {
            return response()->json(['error' => 'Invalid or inaccessible directory.'], 400);
        }

        try {
            $matchingFiles = [];
            
            if ($recursive) {
                $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($searchPath));
            } else {
                $iterator = new \DirectoryIterator($searchPath);
            }

            foreach ($iterator as $file) {
                if ($file->isDot() || $file->isDir()) {
                    continue;
                }

                $filePath = $file->getPathname();
                $content = file_get_contents($filePath);

                if ($content !== false && preg_match('~' . $regex . '~', $content)) {
                    // Calculate relative path from the search directory
                    $relative = str_replace($searchPath . DIRECTORY_SEPARATOR, '', $filePath);
                    $matchingFiles[] = $relative;
                }
            }

            return response()->json(['files' => $matchingFiles], 200);

        } catch (Exception $e) {
            return response()->json(['error' => 'Internal server error: ' . $e->getMessage()], 500);
        }
    }
}