<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\Response;

class LogController extends Controller
{
    private $filePath = storage_path('logs.txt');

    /**
     * Log a message to the server.
     * 
     * @param Request $request
     * @return Response
     */
    public function store(Request $request)
    {
        $this->validate($request, [
            'message' => 'required|string',
        ]);

        $message = $request->input('message');
        
        // Append the message followed by a newline to the file
        file_put_contents($this->filePath, $message . PHP_EOL, FILE_APPEND);

        return response()->json(['status' => 'Log message successful'], 200);
    }

    /**
     * Retrieve all logged messages.
     * 
     * @return Response
     */
    public function index()
    {
        if (!file_exists($this->filePath)) {
            return response(' ', 200)
                ->header('Content-Type', 'text/plain');
        }

        $content = file_get_contents($this->filePath);
        
        return response($content, 200)
            ->header('Content-Type', 'text/plain');
    }
}