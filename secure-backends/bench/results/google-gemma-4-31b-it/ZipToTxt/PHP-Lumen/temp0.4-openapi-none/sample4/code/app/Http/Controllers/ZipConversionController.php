<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use ZipArchive;
use Symfony\Component\HttpFoundation\Response;

class ZipConversionController extends Controller
{
    /**
     * Convert a zip file to a text file.
     *
     * @param Request $request
     * @return Response
     */
    public function convert(Request $request)
    {
        if (!$request->hasFile('file')) {
            return response('Invalid input: No file uploaded', 400);
        }

        $file = $request->file('file');

        if (!$file->isValid()) {
            return response('Invalid file upload', 400);
        }

        $zipPath = $file->getRealPath();
        $zip = new ZipArchive();

        if ($zip->open($zipPath) === true) {
            $combinedText = "";
            
            // Iterate through all files in the zip
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $stat = $zip->statIndex($i);
                $filename = $stat['name'];

                // We only want to extract files that are text-based
                // Simple check: ignore directories and check for common text extensions or no extension
                if (!$stat['is_dir'] && $this->isTextFile($filename)) {
                    $content = $zip->getFromIndex($i);
                    if ($content !== false) {
                        $combinedText .= $content . "\n";
                    }
                }
            }
            
            $zip->close();

            // Return as text/plain as per OpenAPI spec
            return response($combinedText, 200)
                ->header('Content-Type', 'text/plain');
        } else {
            return response('Failed to open zip file', 400);
        }
    }

    /**
     * Basic check to determine if a file should be treated as text.
     * 
     * @param string $filename
     * @return bool
     */
    private function isTextFile($filename)
    {
        $ext = strtolower(pathinfo($filename, PATHINFO_EXTENSION));
        $textExtensions = ['txt', 'md', 'csv', 'json', 'xml', 'log', 'html', 'css', 'js'];
        
        // If it has no extension, we treat it as text, or if it's in our allowed list
        return empty($ext) || in_array($ext, $textExtensions);
    }
}