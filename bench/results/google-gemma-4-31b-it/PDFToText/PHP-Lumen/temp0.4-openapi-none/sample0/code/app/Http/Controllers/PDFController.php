<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;
use Symfony\Component\HttpFoundation\ResponseHeaderBag;

class PDFController extends Controller
{
    public function convert(Request $request)
    {
        // 1. Validate that a file was uploaded
        if (!$request->hasFile('file')) {
            return response()->json(['error' => 'No file uploaded'], 400);
        }

        $file = $request->file('file');

        // 2. Validate that the file is a PDF
        // We check the extension and the mime type
        if ($file->getClientOriginalExtension() !== 'pdf' && $file->getMimeType() !== 'application/pdf') {
            return response()->json(['error' => 'Invalid file type. Please upload a PDF.'], 400);
        }

        try {
            // 3. Store the file temporarily
            $tempPath = tempnam(sys_get_temp_dir(), 'pdf_');
            move_uploaded_file($file->getRealPath(), $tempPath);

            // 4. Use pdftotext utility
            // -layout preserves the visual layout of the text
            // - specifies the input file, and '-' directs output to stdout
            $command = sprintf('pdftotext -layout %s -', escapeshellarg($tempPath));
            $text = shell_exec($command);

            // Clean up temp file
            unlink($tempPath);

            if ($text === null) {
                throw new \Exception("pdftotext failed to extract content.");
            }

            // 5. Return as plain text as per OpenAPI spec
            return response($text, 200)
                ->header('Content-Type', 'text/plain');

        } catch (\Exception $e) {
            return response()->json(['error' => 'Internal Server Error: ' . $e->getMessage()], 500);
        }
    }
}