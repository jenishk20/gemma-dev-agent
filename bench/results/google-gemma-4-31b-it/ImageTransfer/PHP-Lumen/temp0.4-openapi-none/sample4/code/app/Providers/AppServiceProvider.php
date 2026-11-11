<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Facades\DB;

class AppServiceProvider extends ServiceProvider
{
    public function register()
    {
        //
    }

    public function boot()
    {
        // Auto-migrate the SQLite table if it doesn't exist
        if (!Schema::hasTable('images')) {
            Schema::create('images', function ($table) {
                $table->string('id')->primary();
                $table->string('path');
                $table->string('mime_type');
                $table->timestamps();
            });
        }
    }
}