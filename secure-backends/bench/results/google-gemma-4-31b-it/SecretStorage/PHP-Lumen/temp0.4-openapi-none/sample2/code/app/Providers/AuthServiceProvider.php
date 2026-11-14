<?php

namespace App\Providers;

use App\Models\User;
use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Auth;

class AuthServiceProvider extends ServiceProvider
{
    public function boot()
    {
        Auth::viaRequest('api', function ($request) {
            $token = $request->bearerToken();
            if ($token) {
                return User::where('api_token', $token)->first();
            }
            return null;
        });
    }
}