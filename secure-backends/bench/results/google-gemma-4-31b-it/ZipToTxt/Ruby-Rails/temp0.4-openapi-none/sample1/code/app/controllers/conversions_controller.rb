class ConversionsController < ApplicationController
  def convert
    file = params[:file]

    if file.nil? || !file.respond_to?(:path)
      return render json: { error: "Invalid input: No file uploaded" }, status: :bad_request
    end

    begin
      # We use a service to handle the logic of extracting and concatenating
      # Note: 'rubyzip' gem is required for Zip::File to work.
      # Since it's not in the provided Gemfile, this assumes the environment 
      # has it or the user adds it. However, to follow instructions strictly:
      result = ZipConverterService.call(file.path)
      
      render plain: result, content_type: 'text/plain'
    rescue => e
      render json: { error: "Conversion failed: #{e.message}" }, status: :bad_request
    end
  end
end