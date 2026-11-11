<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

class CreateServiceStatusesTable extends Migration
{
    public function up()
    {
        Schema::create('service_statuses', function (Blueprint $table) {
            $table->string('serviceId')->primary();
            $table->string('token');
            $table->dateTime('lastNotification');
        });
    }

    public function down()
    {
        Schema::dropIfExists('service_statuses');
    }
}