require 'open3'
require 'fileutils'

class ExtractController < ApplicationController
  def create
    video_file = params[:video]
    frame_number = params[:frameNumber].to_i
    video_filename = params[:videoFileName]

    if video_file.nil? || frame_number <= 0
      return render json: { error: "Missing video file or invalid frame number" }, status: :bad_request
    end

    # Create a temporary directory for this request
    tmp_dir = Dir.mktmpdir("frame_extract_")
    input_path = File.join(tmp_dir, "input_#{video_filename}")
    output_path = File.join(tmp_dir, "output_frame.png")

    begin
      # Save the uploaded file to disk
      File.open(input_path, 'wb') do |file|
        file.write(video_file.read)
      end

      # ffmpeg command: 
      # -i: input file
      # -vf "select=not(mod(n,1))": select frames (n is frame index)
      # -vframes 1: output exactly one frame
      # We use the filter 'select=eq(n,X)' to get exactly the X-th frame
      # Note: ffmpeg frame indices are 0-based. 
      # If the API expects 1-based indexing, we subtract 1. 
      # Based on the example 132, we'll treat it as a 0-based index for ffmpeg.
      cmd = "ffmpeg -i #{Shellwords.escape(input_path)} -vf \"select=eq(n,#{frame_number})\" -vframes 1 #{Shellwords.escape(output_path)}"
      
      stdout, stderr, status = Open3.capture3(cmd)

      if status.success? && File.exist?(output_path)
        send_file output_path, type: 'image/png', disposition: 'inline'
      else
        render json: { error: "Frame at index #{frame_number} could not be found." }, status: :not_found
      end
    rescue StandardError => e
      render json: { error: "Internal Server Error: #{e.message}" }, status: :internal_server_error
    ensure
      # Cleanup temporary files
      FileUtils.remove_entry(tmp_dir) if File.exist?(tmp_dir)
    end
  end
end