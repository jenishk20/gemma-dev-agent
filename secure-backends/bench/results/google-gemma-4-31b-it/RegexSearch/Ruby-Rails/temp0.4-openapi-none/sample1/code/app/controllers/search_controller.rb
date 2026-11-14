class SearchController < ApplicationController
  def index
    regex_param = params[:regex]
    directory_param = params[:directory] || ""
    recursive_param = params[:recursive] == 'true'

    if regex_param.blank?
      return render json: { error: "regex parameter is required" }, status: :bad_request
    end

    begin
      # Validate regex syntax
      Regexp.new(regex_param)
    rescue RegexpError => e
      return render json: { error: "Invalid regex: #{e.message}" }, status: :bad_request
    end

    # Define the root files directory
    root_path = Rails.root.join('files')
    
    # Resolve the search directory and ensure it is within the root_path to prevent directory traversal
    search_path = File.expand_path(File.join(root_path, directory_param))
    unless search_path.start_with?(root_path.to_s)
      return render json: { error: "Directory access denied" }, status: :bad_request
    end

    unless Dir.exist?(search_path)
      return render json: { error: "Directory not found" }, status: :bad_request
    end

    begin
      pattern = Regexp.new(regex_param)
      matching_files = []

      # Determine search glob
      glob = recursive_param ? "**/*" : "*"
      
      Dir.glob(File.join(search_path, glob)).each do |path|
        next if File.directory?(path)

        begin
          # Read file content and check for regex match
          # Using File.read is acceptable for standard text files as per requirements
          content = File.read(path)
          if content =~ pattern
            # Calculate path relative to the search directory
            relative_path = path.sub("#{search_path}/", "")
            matching_files << relative_path
          end
        rescue => e
          # Skip files that cannot be read (permissions, binary files, etc.)
          next
        end
      end

      render json: { files: matching_files }, status: :ok
    rescue => e
      render json: { error: "Internal server error: #{e.message}" }, status: :internal_server_error
    end
  end
end