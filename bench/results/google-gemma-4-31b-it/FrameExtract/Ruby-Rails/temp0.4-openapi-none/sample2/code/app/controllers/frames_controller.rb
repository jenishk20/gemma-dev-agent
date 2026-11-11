require 'open3'
require 'fileutils'

class FramesController < ApplicationController
  def extract
    video_file = params[:video]
    frame_number = params[:frameNumber].to_i
    
    if video_file.nil? || frame_number <= 0
      return render json: { error: "Invalid input parameters" }, status: :bad_request
    end

    # Create a temporary directory for processing
    tmp_dir = Dir.mktmpdir("frame_extract")
    input_path = File.join(tmp_dir, "input_video")
    output_path = File.join(tmp_dir, "frame.png")

    begin
      # Save uploaded file to disk
      File.open(input_path, 'wb') do |file|
        file.write(video_file.read)
      end

      # ffmpeg command:
      # -i: input file
      # -vf "select=eq(n\,FRAME_INDEX)": selects the specific frame index (0-based)
      # -vframes 1: output exactly one frame
      # -f image2: output format as image
      cmd = "ffmpeg -i #{Shellwords.escape(input_path)} -vf \"select=eq(n,#{frame_number})\" -vframes 1 -f image2 #{Shellwords.escape(output_path)}"
      
      stdout, stderr, status = Open3.capture3(cmd)

      if status.success? && File.exist?(output_path)
        # Send the image file as PNG
        send_file output_path, type: 'image/png', disposition: 'inline'
      else
        render json: { error: "Frame at index #{frame_number} could not be found." }, status: :not_found
      end
    rescue StandardError => e
      render json: { error: "Processing error: #{e.message}" }, status: :internal_server_error
    ensure
      # Cleanup temporary files
      FileUtils.remove_entry(tmp_dir) if tmp_dir && Dir.exist?(tmp_dir)
    end
  end
end