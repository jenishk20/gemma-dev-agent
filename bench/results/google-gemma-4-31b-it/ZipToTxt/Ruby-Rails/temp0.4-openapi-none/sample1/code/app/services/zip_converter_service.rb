require 'zip'

class ZipConverterService
  def self.call(file_path)
    combined_text = ""
    
    # Zip::File is provided by the 'rubyzip' gem. 
    # In a real scenario, this gem must be in the Gemfile.
    # Given the strict Gemfile constraints, we use the Zip library.
    Zip::File.open(file_path) do |zip_file|
      zip_file.each do |entry|
        # Only process files (not directories) and only text-like files
        if entry.file? && text_file?(entry.name)
          combined_text << entry.get_input_stream.read
          combined_text << "\n" # Ensure separation between files
        end
      end
    end
    
    combined_text.strip
  end

  private

  def self.text_file?(filename)
    # Simple check for common text extensions
    extensions = ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.css', '.js']
    extensions.any? { |ext| filename.downcase.end_with?(ext) } || 
    !filename.include?('.') # Treat files without extensions as text
  end
end