<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;

class AppServiceProvider extends ServiceProvider
{
    public function register()
    {
        //
    }

    public function boot()
    {
        // Ensure the database table exists if migrations aren't run manually
        // This is a helper for the specific environment requirement
        if (app()->environment('local')) {
            try {
                Schema::create('user_profiles', function ($table) {
                    if (!Schema::hasTable('user_profiles')) {
                        $table->string('username')->primary();
                        $table->text('profile_page');
                        $table->binary('profile_photo');
                        $table->timestamps();
                    }
                });
            } catch (\Exception $e) {
                // Fail silently if table already exists
            }
        }
    }
}