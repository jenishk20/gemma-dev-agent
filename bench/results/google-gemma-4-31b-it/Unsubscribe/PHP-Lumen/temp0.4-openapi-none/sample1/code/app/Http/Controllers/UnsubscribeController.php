<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class UnsubscribeController extends Controller
{
    public function decide(Request $request): JsonResponse
    {
        // The request body is expected to be text/plain raw email content
        $rawEmail = $request->getContent();

        if (empty($rawEmail)) {
            return response()->json(['error' => 'Empty request body'], 400);
        }

        // 1. Extract Email Address from "From:" header
        // Regex looks for "From:" followed by optional name and the email in <brackets> or just the email
        $email = $this->extractEmail($rawEmail);

        // 2. Determine if the user wants to unsubscribe
        $shouldUnsubscribe = $this->checkUnsubscribeIntent($rawEmail);

        return response()->json([
            'email' => $email,
            'unsubscribe' => $shouldUnsubscribe
        ], 200);
    }

    private function extractEmail(string $content): string
    {
        // Matches "From: Name <email@domain.com>" or "From: email@domain.com"
        if (preg_match('/^From:\s*(?:.*<)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:>)?/m', $content, $matches)) {
            return $matches[1];
        }

        return 'unknown';
    }

    private function checkUnsubscribeIntent(string $content): bool
    {
        $keywords = [
            'unsubscribe',
            'remove me',
            'deregister me',
            'stop sending me',
            'delete me'
        ];

        // Convert to lowercase for case-insensitive matching
        $lowerContent = strtolower($content);

        foreach ($keywords as $keyword) {
            if (str_contains($lowerContent, $keyword)) {
                return true;
            }
        }

        return false;
    }
}