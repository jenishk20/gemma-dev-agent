<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class UnsubscribeController extends Controller
{
    /**
     * Decides if a user wants to be unsubscribed based on raw email content.
     *
     * @param Request $request
     * @return JsonResponse
     */
    public function decide(Request $request): JsonResponse
    {
        $rawContent = $request->getContent();

        if (empty($rawContent)) {
            return response()->json(['email' => null, 'unsubscribe' => false], 200);
        }

        // 1. Extract Email Address from "From:" header
        // Regex looks for From: Name <email@domain.com> or From: email@domain.com
        $email = null;
        if (preg_match('/^From:\s*(?:.*<)?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:>)?/mi', $rawContent, $matches)) {
            $email = $matches[1];
        }

        // 2. Decide Unsubscribe status
        // Keywords: "unsubscribe", "remove me", "deregister me", "stop sending me", "delete me"
        $keywords = [
            'unsubscribe',
            'remove me',
            'deregister me',
            'stop sending me',
            'delete me'
        ];

        $shouldUnsubscribe = false;
        $lowerContent = strtolower($rawContent);

        foreach ($keywords as $keyword) {
            if (str_contains($lowerContent, $keyword)) {
                $shouldUnsubscribe = true;
                break;
            }
        }

        return response()->json([
            'email' => $email,
            'unsubscribe' => $shouldUnsubscribe
        ], 200);
    }
}