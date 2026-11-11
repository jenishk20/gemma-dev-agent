<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateWikiTables extends Migration
{
    public function up()
    {
        Schema::create('entries', function (Blueprint $table) {
            $table->id();
            $table->string('title');
            $table->text('content');
            $table->string('last_modified_by');
            $table->timestamps();
        });

        Schema::create('entry_edits', function (Blueprint $table) {
            $table->id();
            $table->foreignId('entry_id')->constrained()->onDelete('cascade');
            $table->text('content');
            $table->string('modified_by');
            $table->string('summary');
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('entry_edits');
        Schema::dropIfExists('entries');
    }
}