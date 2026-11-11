<?php

namespace App\Http\Middleware;

use Closure;
use App\Models\Merchant;
use Illuminate\Support\Facades\Cookie;

class Authenticate
{
    public function handle($request, Closure $next)
    {
        $token = $request->cookie('AUTH_COOKIE');
        
        if (!$token) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $merchant = Merchant::find($token);
        if (!$merchant) {
            return response()->json(['error' => 'Unauthorized'], 401);
        }

        $request->setUserResolver(function () use ($merchant) {
            return $merchant;
        });

        return $next($request);
    }
}