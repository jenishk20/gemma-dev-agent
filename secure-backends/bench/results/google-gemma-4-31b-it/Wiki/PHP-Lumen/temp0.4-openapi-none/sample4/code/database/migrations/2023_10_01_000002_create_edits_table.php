<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateEditsTable extends Migration
{
    public function up()
    {
        Schema::create('edits', function (Blueprint $table) {
            $table->id();
            $table->foreignId('entry_id');
            $table->text('content');
            $table->string('modified_by');
            $table->string('summary')->nullable();
            $table->timestamps();
        });
    }

    public function down()
    {
        Schema::dropIfExists('edits');
    }
}