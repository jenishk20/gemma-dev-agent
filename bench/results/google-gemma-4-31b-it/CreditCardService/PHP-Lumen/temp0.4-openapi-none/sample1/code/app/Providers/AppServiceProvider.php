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
        // Auto-run migrations for the sqlite database on startup for convenience in this environment
        if (app()->environment('local')) {
            try {
                // This is a simplified way to ensure the table exists for the challenge
                DB::statement("CREATE TABLE IF NOT EXISTS card_phone (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    credit_card TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    UNIQUE(credit_card, phone)
                )");
                DB::statement("CREATE INDEX IF NOT EXISTS idx_phone ON card_phone(phone)");
            } catch (\Exception $e) {
                // Fail silently or log
            }
        }
    }
}