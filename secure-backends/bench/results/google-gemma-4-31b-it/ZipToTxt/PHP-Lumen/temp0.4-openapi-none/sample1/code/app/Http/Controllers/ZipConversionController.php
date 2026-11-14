<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use ZipArchive;

class ZipConversionController extends Controller
{
    public function convert(Request $request)
    {
        // Validate that a file was uploaded
        if (!$request->hasFile('file')) {
            return response('Invalid input: No file uploaded', 400)
                ->header('Content-Type', 'text/plain');
        }

        $file = $request->file('file');

        // Validate that the file is a zip archive
        if ($file->getClientOriginalExtension() !== 'zip' && $file->getMimeType() !== 'application/zip') {
            return response('Invalid input: File must be a ZIP archive', 400)
                ->header('Content-Type', 'text/plain');
        }

        $zipPath = $file->getRealPath();
        $zip = new ZipArchive();

        if ($zip->open($zipPath) === true) {
            $combinedText = "";
            
            // Iterate through all files in the zip
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $filename = $zip->getNameIndex($i);
                
                // Skip directories
                if (substr($filename, -1) === '/' || $zip->statIndex($i)['type'] === 'dir') {
                    continue;
                }

                // Read content of the file
                $content = $zip->getFromIndex($i);
                if ($content !== false) {
                    $combinedText .= $content . "\n";
                }
            }
            
            $zip->close();

            // Return the concatenated text as plain text
            return response($combinedText, 200)
                ->header('Content-Type', 'text/plain');
        } else {
            return response('Invalid input: Could not open ZIP file', 400)
                ->header('Content-Type', 'text/plain');
        }
    }
}