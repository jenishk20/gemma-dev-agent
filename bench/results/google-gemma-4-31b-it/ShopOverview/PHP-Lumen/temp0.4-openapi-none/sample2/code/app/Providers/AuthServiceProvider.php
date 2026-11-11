<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Auth;
use App\Models\Merchant;
use Illuminate\Support\Facades\Cookie;

class AuthServiceProvider extends ServiceProvider
{
    public function boot()
    {
        Auth::viaRequest('api', function ($request) {
            $cookie = $request->cookie('AUTH_COOKIE');
            if ($cookie) {
                try {
                    $id = decrypt($cookie);
                    return Merchant::find($id);
                } catch (\Exception $e) {
                    return null;
                }
            }
            return null;
        });
    }
}