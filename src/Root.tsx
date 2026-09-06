import {Composition} from 'remotion';
import {VIDEO} from './config';
import {ELEMENTS} from './elements/registry';

export const Root: React.FC = () => (
  <>
    {ELEMENTS.map((el) => (
      <Composition
        key={el.id}
        id={el.id}
        component={el.component}
        defaultProps={el.props}
        durationInFrames={el.durationInFrames}
        fps={VIDEO.fps}
        width={VIDEO.width}
        height={VIDEO.height}
      />
    ))}
  </>
);
