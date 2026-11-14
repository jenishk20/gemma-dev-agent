<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;

class LogController extends Controller
{
    private $filePath;

    public function __construct()
    {
        // Define the path to the logs.txt file in the storage directory
        $this->filePath = storage_path('logs.txt');
    }

    /**
     * Log a message to the server.
     * POST /log
     */
    public function store(Request $request)
    {
        $this->validate($request, [
            'message' => 'required|string',
        ]);

        $message = $request->input('message');
        
        // Append the message followed by a newline character to the file
        file_put_contents($this->filePath, $message . PHP_EOL, FILE_APPEND);

        return response()->json(['status' => 'Log message successful'], 200);
    }

    /**
     * Retrieve all logged messages.
     * GET /logs
     */
    public function index()
    {
        if (!file_exists($this->filePath)) {
            return response('', 200)->header('Content-Type', 'text/plain');
        }

        // Read the entire content of the file
        $content = file_get_contents($this->filePath);

        return response($content, 200)->header('Content-Type', 'text/plain');
    }
}