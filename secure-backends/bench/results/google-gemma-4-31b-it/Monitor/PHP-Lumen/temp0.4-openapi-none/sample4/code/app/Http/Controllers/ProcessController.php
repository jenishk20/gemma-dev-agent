<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class ProcessController extends Controller
{
    /**
     * Retrieve a list of running processes based on a regex filter.
     *
     * @param Request $request
     * @return JsonResponse
     */
    public function getProcesses(Request $request): JsonResponse
    {
        // Validate request body
        $this->validate($request, [
            'command_regex' => 'required|string',
            'filter_flags' => 'string',
        ]);

        $regex = $request->input('command_regex');
        $flags = $request->input('filter_flags', 'aux');

        // Sanitize flags to prevent command injection
        // Only allow alphanumeric characters, spaces, and dashes
        $safeFlags = preg_replace('/[^a-zA-Z0-9\s\-]/', '', $flags);
        
        // Execute ps command
        // We use escapeshellcmd or simply construct the string carefully.
        // Since we are on a server environment, we execute the shell command.
        $command = "ps " . $safeFlags;
        $output = shell_exec($command);

        if ($output === null) {
            return response()->json([
                'code' => 500,
                'message' => 'Failed to execute ps command'
            ], 500);
        }

        $lines = explode("\n", trim($output));
        
        // The first line is usually the header (PID, TTY, TIME, CMD etc)
        // We skip the header
        $header = array_shift($lines);
        
        $results = [];

        foreach ($lines as $line) {
            if (empty(trim($line))) continue;

            // Use regex to filter the process string
            if (preg_match('/' . $regex . '/', $line)) {
                // Extract PID. In 'aux' format, PID is the second column.
                // We split by whitespace.
                $parts = preg_split('/\s+/', trim($line));
                
                // Based on 'aux' output: USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND
                // PID is index 1.
                $pid = isset($parts[1]) ? (int)$parts[1] : 0;
                
                $results[] = [
                    'processId' => $pid,
                    'processString' => $line
                ];
            }
        }

        return response()->json($results, 200);
    }
}